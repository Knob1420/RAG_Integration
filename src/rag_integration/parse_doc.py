"""TASK-P01-FULL-PIPELINE: R6 旧 DOC → LibreOffice 转 docx → 走 R4 解析。

禁用 antiword 兜底（实测 cjk_ratio 0.06 丢中文，宁可 FAILED）。
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .models import DocumentElement, RouteId
from .parse_docx import parse_docx


def convert_doc_to_docx(path: Path) -> Path:
    """headless 转换到临时目录，返回 docx 路径。失败抛异常（→FAILED）。"""
    td = tempfile.mkdtemp(prefix="doc2docx_")
    r = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "docx",
         "--outdir", td, str(path)],
        capture_output=True, text=True, timeout=180)
    out = Path(td) / (path.stem + ".docx")
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"libreoffice convert failed: {r.stderr[:200]}")
    return out


def parse_doc(path: Path, source_id: str, route_reason: str) -> list[DocumentElement]:
    converted = convert_doc_to_docx(path)
    return parse_docx(converted, source_id, RouteId.R6,
                      route_reason + " | via libreoffice docx")
