"""TASK-P01-FULL-PIPELINE: R3/R2 扫描页 MinerU OCR。

子进程调 mineru env CLI（Memory 项目已验证的调用方式）。
R2 单页/连续段用 -s/-e（0 起始），page_offset 映射回原文档页号。
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from .models import (DocumentElement, ElementType, ExtractionMode, Location,
                     Provenance, RouteId)

MINERU_TIMEOUT = 1800  # 109 页实测 ~4.5min；上限 30min
# ponytail: 复用 memory env 的 MinerU（mineru env 是无 torch 的轻量客户端版）
MINERU_ENV = "memory"
MINERU_CMD = ["conda", "run", "--no-capture-output", "-n", MINERU_ENV,
              "env", "CUDA_DEVICE_ORDER=PCI_BUS_ID", "CUDA_VISIBLE_DEVICES=2",
              "mineru"]


def mineru_version() -> str:
    global _ver
    if _ver is None:
        r = subprocess.run(MINERU_CMD + ["--version"], capture_output=True,
                           text=True, timeout=60)
        _ver = (r.stdout.strip() or "?").split()[-1]
    return _ver


_ver: str | None = None


def run_mineru(pdf: Path, start: int | None = None,
               end: int | None = None) -> list[dict]:
    """跑 MinerU，返回 content_list 条目。失败抛异常（→FAILED/PENDING_REVIEW 由上层定）。"""
    with tempfile.TemporaryDirectory(prefix="mineru_") as out_dir:
        cmd = MINERU_CMD + ["-p", str(pdf), "-o", out_dir,
                            "-b", "hybrid-engine", "--effort", "medium",
                            "-l", "ch"]
        if start is not None:
            cmd += ["-s", str(start)]
        if end is not None:
            cmd += ["-e", str(end)]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=MINERU_TIMEOUT)
        if r.returncode != 0:
            tail = (r.stderr or r.stdout)[-500:]
            raise RuntimeError(f"mineru rc={r.returncode}: {tail}")
        lists = list(Path(out_dir).rglob("*content_list.json"))
        if not lists:
            raise RuntimeError("mineru no content_list.json")
        return json.loads(lists[0].read_text(encoding="utf-8"))


class _TableParser(HTMLParser):
    """MinerU table_body（html）→ 行列表。"""
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def html_table_rows(table_body: str) -> list[list[str]]:
    p = _TableParser()
    p.feed(table_body)
    return p.rows


def split_title_row(rows: list[list[str]]) -> tuple[str | None, list[list[str]]]:
    """表首行是标题行（仅一格非空=colspan 表题，或整行同值=合并痕迹）→ (标题, 剩余行)。

    与 xlsx/docx 的 merged_title 规则同构；pdf 两路共用。
    """
    if not rows:
        return None, rows
    nonempty = [v for v in rows[0] if v]
    if nonempty and (len(nonempty) == 1 or
                     (len(set(nonempty)) == 1 and len(nonempty) == len(rows[0]))):
        return nonempty[0], rows[1:]
    return None, rows


def ocr_elements(items: list[dict], source_id: str, route: RouteId,
                 route_reason: str, page_offset: int = 0
                 ) -> tuple[list[DocumentElement], Provenance]:
    """content_list → Elements。page = page_idx + page_offset + 1（物理页号 1 起）。"""
    prov = Provenance(parser_name="mineru", parser_version=mineru_version(),
                      route=route, extraction_mode=ExtractionMode.TEXT_OCR,
                      route_reason=route_reason)
    elements: list[DocumentElement] = []
    table_idx = 0
    for idx, it in enumerate(items):
        page = it.get("page_idx", 0) + page_offset + 1
        t = it.get("type")
        if t == "text" and (txt := (it.get("text") or "").strip()):
            lvl = it.get("text_level")  # MinerU 标题级别 → HEADING
            elements.append(DocumentElement(
                source_id=source_id,
                element_type=ElementType.HEADING if lvl else ElementType.PARAGRAPH,
                content=txt,
                location=Location(source_id, page_no=page, block_no=idx + 1),
                provenance=prov,
                metadata={"level": lvl} if lvl else {}))
        elif t == "table":
            rows = html_table_rows(it.get("table_body") or "")
            if len(rows) < 2:
                continue
            table_idx += 1
            consumed = 0  # 标题行数（表题/检查时间/检查人员等 colspan 行）
            while len(rows) > 1:
                title, rest = split_title_row(rows)
                if title is None:
                    break
                consumed += 1
                elements.append(DocumentElement(
                    source_id=source_id, element_type=ElementType.KEY_VALUE,
                    content=title,
                    location=Location(source_id, page_no=page,
                                      table_index=table_idx, row_no=consumed),
                    provenance=prov, metadata={"merged_title": True}))
                rows = rest
            if len(rows) < 2:
                continue  # 只剩表头无数据行
            header = rows[0]
            for ri, row in enumerate(rows[1:], start=consumed + 2):
                if not any(row):
                    continue
                elements.append(DocumentElement(
                    source_id=source_id, element_type=ElementType.TABLE_ROW,
                    content=" | ".join(row),
                    location=Location(source_id, page_no=page,
                                      table_index=table_idx, row_no=ri),
                    provenance=prov,
                    metadata={"header": header,
                              "detection_method": "ocr_layout"}))
        elif t == "image":
            elements.append(DocumentElement(
                source_id=source_id, element_type=ElementType.FIGURE,
                content="[figure]",
                location=Location(source_id, page_no=page, block_no=idx + 1),
                provenance=prov))
    return elements, prov
