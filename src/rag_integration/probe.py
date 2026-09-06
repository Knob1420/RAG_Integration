"""TASK-P01-FULL-PIPELINE: 轻量文件探测（路由前置信号）。

全部信号结构化可得（P01-parser-routing.md 约束）：字符数/图像覆盖率/zip 条目名/sheet 形态。
不提取正文，只产出计数与判定。
"""
from __future__ import annotations

import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .models import PageType

SUPPORTED_EXTS = {"pdf", "docx", "doc", "xlsx", "ppt", "pptx"}
SCAN_CHARS = 50          # 文字页下限（chars/页）
SCAN_IMG_COVER = 0.70    # 实测校准：扫描页图幅含页边距，覆盖率 0.74-0.81（设计稿 85% 过严）


@dataclass
class ProbeResult:
    path: Path
    ext: str                       # 无点小写
    pages: int = 0                 # pdf 页数
    page_types: list[PageType] = field(default_factory=list)
    wps_backslash: bool = False    # docx/xlsx zip 条目含反斜杠
    xlsx_complex_reasons: list[str] = field(default_factory=list)
    error: Optional[str] = None    # 探测本身失败（zip 损坏等）


def normalize_zip(path: Path) -> Path:
    """WPS zip 条目反斜杠修复：临时副本重写条目名，原始文件不动。docx/xlsx 通用。"""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except zipfile.BadZipFile:
        return path
    if not any("\\" in n for n in names):
        return path
    tmp = Path(tempfile.mkdtemp(prefix="wpsfix_")) / path.name
    with zipfile.ZipFile(path) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            info = zipfile.ZipInfo(item.filename.replace("\\", "/"),
                                   date_time=item.date_time)
            info.compress_type = item.compress_type
            zout.writestr(info, zin.read(item.filename))
    return tmp


def _max_image_cover(page) -> float:
    """页内最大图像 bbox 覆盖率（与页面面积之比）。"""
    import fitz
    area = abs(page.rect)
    best = 0.0
    for info in page.get_image_info():
        bbox = fitz.Rect(info["bbox"])
        w, h = max(0, bbox.width), max(0, bbox.height)
        best = max(best, (w * h) / max(area, 1.0))
    return best


def classify_pages(path: Path) -> list[PageType]:
    """PDF 页级双信号分类：chars + 最大图覆盖率。"""
    import fitz
    out = []
    with fitz.open(path) as doc:
        for page in doc:
            chars = len(page.get_text().strip())
            cover = _max_image_cover(page)
            if chars >= SCAN_CHARS:
                out.append(PageType.TEXT)
            elif cover >= SCAN_IMG_COVER:
                out.append(PageType.SCAN)
            else:
                out.append(PageType.EMPTY)
    return out


def _xlsx_signals(path: Path) -> list[str]:
    """R8 复杂信号：合并单元格/多行表头/公式/多 sheet 关联。"""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=False, read_only=False)
    reasons = []
    merged = multi_head = formulas = 0
    for ws in wb.worksheets:
        merged += len(ws.merged_cells.ranges)
        formulas += sum(
            1 for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and c.value.startswith("="))
        first = [c.value for c in next(ws.iter_rows(max_row=1))]
        if any(c is None for c in first) and len(first) > 2:
            multi_head += 1
    if merged:
        reasons.append(f"merged={merged}")
    if multi_head:
        reasons.append(f"multi_header_sheets={multi_head}")
    if formulas:
        reasons.append(f"formulas={formulas}")
    wb.close()
    return reasons


def probe(path: Path) -> ProbeResult:
    ext = path.suffix.lstrip(".").lower()
    r = ProbeResult(path=path, ext=ext)
    try:
        if ext == "pdf":
            r.page_types = classify_pages(path)
            r.pages = len(r.page_types)
        elif ext in ("docx", "xlsx"):
            with zipfile.ZipFile(path) as z:
                r.wps_backslash = any("\\" in n for n in z.namelist())
            if ext == "xlsx":
                r.xlsx_complex_reasons = _xlsx_signals(normalize_zip(path))
        elif ext in ("doc", "ppt", "pptx"):
            pass  # 路由不需要额外探测
        else:
            pass  # R9 在 routing 判
    except Exception as e:  # zip 损坏/文件不可读 → 探测失败即 FAILED
        r.error = f"{type(e).__name__}: {e}"
    return r
