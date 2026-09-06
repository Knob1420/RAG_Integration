"""TASK-P01-FULL-PIPELINE: R1/R2/R3 PDF 解析 → DocumentElement。

R1 全文字页：fitz 文本块（表格 bbox 区内块剔除）+ pdfplumber 线框表 + 插图占位。
R2 混合：文字页走 R1 路径；扫描页连续段调 MinerU（-s/-e + 页偏移）。
R3 全扫描：整文件 MinerU。
首版表格检测只做 lattice（线框）；stream 表降级为文本块（记质量报告已知缺口）。
"""
from __future__ import annotations

from pathlib import Path

import fitz
import pdfplumber

from . import ocr_mineru
from .models import (DocumentElement, ElementType, ExtractionMode, Location,
                     PageType, Provenance, RouteId)
from .probe import classify_pages


def _toc_chains(doc: fitz.Document) -> dict[int, tuple[str, ...]]:
    """物理页号(1起) → 章节链（书签）。无书签 → 空链。"""
    toc = doc.get_toc()  # [level, title, page(1起)]
    res: dict[int, tuple[str, ...]] = {}
    stack: list[str] = []
    i = 0
    for p in range(1, doc.page_count + 1):
        while i < len(toc) and toc[i][2] <= p:
            lvl, title, _ = toc[i]
            stack = stack[: lvl - 1] + [title]
            i += 1
        res[p] = tuple(stack)
    return res


def _native_page_elements(page, pno: int, chain: tuple[str, ...],
                          plumb_page, prov: Provenance,
                          source_id: str) -> list[DocumentElement]:
    """单文字页：表格行 + 表格外文本块 + 插图占位。"""
    out: list[DocumentElement] = []
    table_idx = getattr(_native_page_elements, "_table_idx", 0)

    tables = plumb_page.find_tables()  # 默认 lines 策略（lattice）
    bboxes = []
    for tb in tables:
        rows = tb.extract()
        if not rows or len(rows) < 2:
            continue
        table_idx += 1
        rows = [[c.strip() if c else "" for c in r] for r in rows]
        consumed = 0  # 标题行（整行合并/单格表题）→ 单条 key_value
        while len(rows) > 1:
            title, rest = ocr_mineru.split_title_row(rows)
            if title is None:
                break
            consumed += 1
            out.append(DocumentElement(
                source_id=source_id, element_type=ElementType.KEY_VALUE,
                content=title,
                location=Location(source_id, page_no=pno,
                                  table_index=table_idx, row_no=consumed,
                                  section_chain=chain),
                provenance=prov, metadata={"merged_title": True}))
            rows = rest
        if len(rows) < 2:
            continue  # 只剩表头无数据行：不加 bbox，该区文本回落到文本块，防丢字
        bboxes.append(fitz.Rect(tb.bbox))
        header = rows[0]
        for ri, row in enumerate(rows[1:], start=consumed + 2):
            vals = row
            if not any(vals):
                continue
            out.append(DocumentElement(
                source_id=source_id, element_type=ElementType.TABLE_ROW,
                content=" | ".join(vals),
                location=Location(source_id, page_no=pno,
                                  table_index=table_idx, row_no=ri,
                                  section_chain=chain),
                provenance=prov,
                metadata={"header": header, "detection_method": "lattice"}))

    block_no = 0
    for b in page.get_text("blocks"):
        if b[6] != 0:  # 非文本块
            continue
        text = b[4].strip()
        if not text:
            continue
        rect = fitz.Rect(b[:4])
        if any(rect.intersects(bx) and abs(rect & bx) > 0.5 * abs(rect)
               for bx in bboxes):
            continue  # 表格区文本已按行产出，不重复
        block_no += 1
        out.append(DocumentElement(
            source_id=source_id, element_type=ElementType.PARAGRAPH,
            content=text,
            location=Location(source_id, page_no=pno, block_no=block_no,
                              section_chain=chain),
            provenance=prov))

    if page.get_images():  # 文字页局部插图 → 占位
        out.append(DocumentElement(
            source_id=source_id, element_type=ElementType.FIGURE,
            content="[figure]",
            location=Location(source_id, page_no=pno, block_no=block_no + 1,
                              section_chain=chain),
            provenance=prov))
    _native_page_elements._table_idx = table_idx
    return out


def _native_prov(route: RouteId, route_reason: str) -> Provenance:
    return Provenance(parser_name="pymupdf+pdfplumber",
                      parser_version=f"{fitz.__version__}+{pdfplumber.__version__}",
                      route=route,
                      extraction_mode=ExtractionMode.TEXT_NATIVE,
                      route_reason=route_reason)


def _scan_runs(page_types: list[PageType]) -> list[tuple[int, int]]:
    """扫描页 0 起索引 → 连续段 [(start, end)]。"""
    runs, start = [], None
    for i, t in enumerate(page_types):
        if t is PageType.SCAN:
            if start is None:
                start = i
        elif start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(page_types) - 1))
    return runs


def parse_pdf(path: Path, source_id: str, route: RouteId, route_reason: str,
              page_types: list[PageType]) -> tuple[list[DocumentElement], dict]:
    elements: list[DocumentElement] = []
    _native_page_elements._table_idx = 0

    if route is RouteId.R3:
        items = ocr_mineru.run_mineru(path)
        els, _ = ocr_mineru.ocr_elements(items, source_id, route, route_reason)
        elements.extend(els)
    else:  # R1 / R2
        prov = _native_prov(route, route_reason)
        scan = {i for i, t in enumerate(page_types) if t is PageType.SCAN}
        with fitz.open(path) as doc, pdfplumber.open(path) as pdf:
            chains = _toc_chains(doc)
            for i, page in enumerate(doc):
                pno = i + 1
                if page_types[i] is PageType.EMPTY:
                    elements.append(DocumentElement(
                        source_id=source_id,
                        element_type=ElementType.PAGE_OMITTED, content="",
                        location=Location(source_id, page_no=pno),
                        provenance=prov,
                        metadata={"page_omitted_reason": "empty_page"}))
                    continue
                if i in scan:
                    continue  # R2 扫描页走 MinerU（下文按连续段处理）
                elements.extend(_native_page_elements(
                    page, pno, chains.get(pno, ()), pdf.pages[i], prov,
                    source_id))
        if route is RouteId.R2 and scan:
            for s, e in _scan_runs(page_types):
                items = ocr_mineru.run_mineru(path, start=s, end=e)
                els, _ = ocr_mineru.ocr_elements(
                    items, source_id, route,
                    f"{route_reason} | ocr pages {s + 1}-{e + 1}",
                    page_offset=s)
                elements.extend(els)
    stats = {"pages": len(page_types),
             "text_pages": sum(t is PageType.TEXT for t in page_types),
             "scan_pages": sum(t is PageType.SCAN for t in page_types),
             "empty_pages": sum(t is PageType.EMPTY for t in page_types)}
    return elements, stats
