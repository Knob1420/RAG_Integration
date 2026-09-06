"""TASK-P01-FULL-PIPELINE: R4/R5/R6 DOCX 解析 → DocumentElement。

R5 先走 WPS zip 修复（临时副本）；R6 由 parse_doc 转换后复用本模块（route=R6）。
python-docx：段落（标题样式层级）+ 表格（首行表头，每行自带表头）+ 内嵌图占位。
"""
from __future__ import annotations

from pathlib import Path

import docx as docx_lib
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .models import (DocumentElement, ElementType, ExtractionMode, Location,
                     Provenance, RouteId)
from .probe import normalize_zip

EXTRACTION_MODE = {
    RouteId.R4: ExtractionMode.DOCX_STRUCTURED,
    RouteId.R5: ExtractionMode.DOCX_STRUCTURED_WPS,
    RouteId.R6: ExtractionMode.DOC_CONVERTED,
}


def _heading_level(style_name: str) -> int | None:
    n = (style_name or "").lower()
    if not n.startswith(("heading", "标题")):
        return None
    digits = "".join(ch for ch in style_name if ch.isdigit())
    return int(digits) if digits else 1


def _provenance(route: RouteId, route_reason: str) -> Provenance:
    name = "python-docx"
    if route is RouteId.R6:
        name = "libreoffice->python-docx"
    return Provenance(parser_name=name,
                      parser_version=docx_lib.__version__,
                      route=route, extraction_mode=EXTRACTION_MODE[route],
                      route_reason=route_reason)


def parse_docx(path: Path, source_id: str, route: RouteId,
               route_reason: str) -> list[DocumentElement]:
    real = normalize_zip(path) if route is RouteId.R5 else path
    d = docx_lib.Document(str(real))
    prov = _provenance(route, route_reason)
    elements: list[DocumentElement] = []
    chain: list[str] = []
    table_idx = 0
    para_seq = 0

    for child in d.element.body.iterchildren():  # 按文档顺序（段落与表格交错）
        tag = child.tag.split("}")[-1]
        if tag == "p":
            para_seq += 1
            p = Paragraph(child, d)
            text = p.text.strip()
            if lv := _heading_level(p.style.name):
                if text:
                    chain = chain[: lv - 1] + [text]  # 截断到当前层
                    elements.append(DocumentElement(
                        source_id=source_id, element_type=ElementType.HEADING,
                        content=text,
                        location=Location(source_id, paragraph_no=para_seq,
                                          section_chain=tuple(chain)),
                        provenance=prov, metadata={"level": lv}))
                continue
            if len(p._p.findall(".//" + qn("w:drawing"))):
                elements.append(DocumentElement(
                    source_id=source_id, element_type=ElementType.FIGURE,
                    content="[figure]",
                    location=Location(source_id, paragraph_no=para_seq,
                                      section_chain=tuple(chain)),
                    provenance=prov))
            if text:
                elements.append(DocumentElement(
                    source_id=source_id, element_type=ElementType.PARAGRAPH,
                    content=text,
                    location=Location(source_id, paragraph_no=para_seq,
                                      section_chain=tuple(chain)),
                    provenance=prov))
        elif tag == "tbl":
            table_idx += 1
            t = Table(child, d)
            rows = [[c.text.strip() for c in row.cells] for row in t.rows]
            if not rows or not any(any(r) for r in rows):
                continue
            if len(rows[0]) == 1:  # 单列表=文本块（封面等）→ 逐行 key_value，无表头语义
                for i, row in enumerate(rows, start=1):
                    if row[0]:
                        elements.append(DocumentElement(
                            source_id=source_id,
                            element_type=ElementType.KEY_VALUE,
                            content=row[0],
                            location=Location(source_id, table_index=table_idx,
                                              row_no=i,
                                              section_chain=tuple(chain)),
                            provenance=prov))
                continue
            # 合并标题行（整行同值=合并痕迹，如封面标题表）→ 单条 key_value
            if rows[0][0] and all(v == rows[0][0] for v in rows[0]):
                elements.append(DocumentElement(
                    source_id=source_id, element_type=ElementType.KEY_VALUE,
                    content=rows[0][0],
                    location=Location(source_id, table_index=table_idx,
                                      row_no=1, section_chain=tuple(chain)),
                    provenance=prov, metadata={"merged_title": True}))
                rows = rows[1:]
                if not rows or not any(any(r) for r in rows):
                    continue
            header = rows[0]
            for i, row in enumerate(rows[1:], start=2):  # row_no 含表头行，2 起
                if not any(row):
                    continue  # 空行不产出（空文本红线）
                elements.append(DocumentElement(
                    source_id=source_id, element_type=ElementType.TABLE_ROW,
                    content=" | ".join(row),
                    location=Location(source_id, table_index=table_idx,
                                      row_no=i, section_chain=tuple(chain)),
                    provenance=prov,
                    metadata={"header": header, "detection_method": "native"}))
    return elements
