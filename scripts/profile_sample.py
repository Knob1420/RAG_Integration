#!/usr/bin/env python3
"""TASK-P00-003B: 分层抽样数据画像.

只输出结构特征与计数，不输出任何正文片段。产出:
- stdout: 每份抽样文件的结构摘要
- docs/reports/P00-sample-log.csv: 结构化抽样日志

用法: python scripts/profile_sample.py   (在 RAG 环境运行)
"""

import csv
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/zjlab/Documents/build_LLMs/NLP_course_hf/RAG/Data/x100研制 - 副本")
OUT_CSV = Path("docs/reports/P00-sample-log.csv")

# 抽样清单: (relative_path, 文档类型)——按类型覆盖选取，非按文件名
SAMPLE = [
    # PDF: 原生导出 vs 盖章扫描两类都要
    ("00_会议纪要/SCS-01-20240712_3D打印卫星搭载计算载荷讨论纪要-李超.pdf", "会议纪要"),
    ("00_会议纪要/2025-08-12_3D打印星智加X100载荷处理方式沟通纪要-签署.pdf", "会议纪要"),
    ("智加X100（硬件）验收测试记录表.pdf", "验收测试"),
    ("3d打印 归档/7_智加X100（硬件）验收测试记录表.pdf", "验收测试"),
    ("3d打印 归档/智加X100模块交付文件盖章/8_智加X100计算模块技术说明书V1.0.docx.pdf", "说明书"),
    # DOCX: 方案/IDS/大纲/总结
    ("04_整体设计方案/20240305-Z0_智加X100星载计算机初样_总体设计方案_20240305.docx", "方案设计"),
    ("02-3D打印卫星计算载荷-智加X100计算模块配套电源模块 IDS表/3D打印卫星计算载荷-智加X100计算模块配套电源模块 IDS表_20240924_签署.docx", "IDS"),
    ("3d打印 归档/6_智加X100计算模块_验收级环境试验大纲_20250120_终稿.docx", "环境试验"),
    ("3d打印 归档/X100计算模块正样件研制与质量总结报告_20250221.docx", "总结报告"),
    ("3d打印 归档/8_智加X100计算模块技术说明书V1.0.docx", "说明书"),
    # DOC: 旧二进制格式（履历书）
    ("3d打印 归档/3_智加X100计算模块_产品履历书.doc", "履历书"),
    ("3d打印 归档/3_智加X100电源模块_产品履历书.doc", "履历书"),
    # XLSX: 清单/版本控制/遥测/程控
    ("01_3D打印卫星_智加X100计算模块交付清单_20250124.xlsx", "交付清单"),
    ("3D打印_软件版本控制.xlsx", "版本控制"),
    ("3D打印星遥控遥测汇总表.xlsx", "遥测汇总"),
    ("程控时间表8.31.xlsx", "程控时间表"),
]

# ── 正文特征只计数，绝不打印值 ──
CODE_RE = re.compile(r"\b[A-Z]{2,}[-/]\d{2,}[A-Z0-9/-]*\b")       # SCS-01 / Z0102 类编号
NUMSEC_RE = re.compile(r"^\s*\d+(\.\d+){1,4}\s*\S", re.M)          # 1.2.3 节标题
VER_RE = re.compile(r"([Vv]\d+(\.\d+)?|版本|修订|Rev)", )
REF_RE = re.compile(r"(引用文件|依据文件|参考文件|相关文件)")
STATUS_WORDS = ["计划", "完成", "通过", "待确认", "建议", "推测"]
FORMULA_HINT = re.compile(r"[=∫∑√±≤≥≈×÷°]|[A-Za-z]\s*[=]\s*[^=]")


def text_features(text: str) -> dict:
    return {
        "chars": len(text),
        "cjk_ratio": round(sum('\u4e00' <= c <= '\u9fff' for c in text) / max(len(text), 1), 2),
        "garbled": text.count("\ufffd"),
        "codes": len(set(CODE_RE.findall(text))),
        "numbered_sections": len(NUMSEC_RE.findall(text)),
        "version_hits": len(VER_RE.findall(text)),
        "ref_file_words": len(REF_RE.findall(text)),
        "status_word_total": sum(text.count(w) for w in STATUS_WORDS),
        "formula_hint": len(FORMULA_HINT.findall(text)) // 100,  # 粗粒度/百次
    }


def profile_pdf(path: Path) -> dict:
    import fitz
    import pdfplumber

    doc = fitz.open(path)
    pages = len(doc)
    toc = len(doc.get_toc())
    images = sum(len(p.get_images()) for p in doc)
    page_texts = [doc[i].get_text() for i in range(pages)]
    doc.close()
    text = "\n".join(page_texts)
    chars_per_page = [len(t) for t in page_texts]
    scan_pages = sum(1 for c in chars_per_page if c < 50)
    # 页眉页脚污染: 出现在 >50% 页面的非空行
    line_sets = [set(t.splitlines()) for t in page_texts if t.strip()]
    rep_lines = 0
    if line_sets:
        common = set.intersection(*line_sets) if len(line_sets) > 1 else set()
        rep_lines = len({l.strip() for l in common if l.strip()})
    # 页码: 尾部含独立数字的页面占比
    pagenum_pages = sum(
        1 for t in page_texts
        if t.splitlines() and re.fullmatch(r"\s*\d{1,3}\s*", t.splitlines()[-1] or "")
    )
    tables = 0
    with pdfplumber.open(path) as pdf:
        for i in range(min(5, len(pdf.pages))):
            tables += len(pdf.pages[i].find_tables())
    f = text_features(text)
    return {
        "pages_or_sheets": pages,
        "scanned": f"疑似扫描页 {scan_pages}/{pages}(chars<50)",
        "toc": f"书签{toc}条",
        "tables": f"前5页检出{tables}个",
        "images": images,
        "page_numbers": f"{pagenum_pages}/{pages}页",
        "header_footer_pollution": rep_lines,
        **f,
    }


def _doc_text_via_libreoffice(path: Path) -> str:
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "txt:Text (encoded)",
             "--outdir", td, str(path)],
            capture_output=True, text=True, timeout=120)
        txts = list(Path(td).glob("*.txt"))
        if r.returncode != 0 or not txts:
            return ""
        return txts[0].read_text(encoding="utf-8", errors="ignore")


def _doc_text_via_antiword(path: Path) -> str:
    r = subprocess.run(["antiword", "-m", "UTF-8.txt", str(path)],
                       capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", errors="ignore") if r.returncode == 0 else ""


def _normalize_docx(path: Path) -> Path:
    """WPS zip 条目反斜杠路径修复版副本（docx/xlsx 通用；不改原始文件）。"""
    import zipfile

    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except zipfile.BadZipFile:
        return path
    if not any("\\" in n for n in names):
        return path
    tmp = Path(tempfile.mkdtemp()) / path.name
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            info = zipfile.ZipInfo(item.filename.replace("\\", "/"), date_time=item.date_time)
            info.compress_type = item.compress_type
            zout.writestr(info, zin.read(item.filename))
    return tmp


def profile_docx(path: Path) -> dict:
    import docx

    path = _normalize_docx(path)
    d = docx.Document(str(path))
    headings = sum(1 for p in d.paragraphs if p.style.name.lower().startswith(("heading", "标题")))
    tables = len(d.tables)
    images = len(d.inline_shapes)
    text = "\n".join(p.text for p in d.paragraphs)
    for t in d.tables:  # 表格文字参与特征计数（不打印）
        for row in t.rows:
            for cell in row.cells:
                text += "\n" + cell.text
    return {
        "pages_or_sheets": "N/A(docx无页)",
        "headings": headings,
        "tables": tables,
        "images": images,
        **text_features(text),
    }


def profile_doc(path: Path) -> dict:
    # libreoffice 优先: antiword 的 UTF-8 映射丢中文（实测 cjk_ratio 仅 0.06）
    text = _doc_text_via_libreoffice(path)
    parser = "libreoffice"
    if not text.strip():
        text = _doc_text_via_antiword(path)
        parser = "antiword"
    return {
        "parser": parser,
        "pages_or_sheets": "N/A",
        "extractable": bool(text.strip()),
        **text_features(text),
    }


def profile_xlsx(path: Path) -> dict:
    import openpyxl

    path = _normalize_docx(path)  # WPS 反斜杠条目同样存在于此格式
    wb = openpyxl.load_workbook(path, data_only=False)
    sheets = []
    formulas = 0
    merged_total = 0
    hidden_rows = hidden_cols = 0
    cells = possible = 0
    code_cols = 0
    multi_header_sheets = 0
    related = set()
    sheet_names = set(wb.sheetnames)
    for ws in wb.worksheets:
        sheets.append(ws.title)
        merged_total += len(ws.merged_cells.ranges)
        hidden_rows += sum(1 for d in ws.row_dimensions.values() if d.hidden)
        hidden_cols += sum(1 for d in ws.column_dimensions.values() if d.hidden)
        first_row_vals = [c.value for c in next(ws.iter_rows(max_row=1))]
        if any(c is None for c in first_row_vals) and len(first_row_vals) > 2:
            multi_header_sheets += 1  # 首行有空 → 疑似多行表头/标题行
        possible += ws.max_row * ws.max_column
        for row in ws.iter_rows():
            for c in row:
                if c.value is None:
                    continue
                cells += 1
                v = str(c.value)
                if v.startswith("="):
                    formulas += 1
                if CODE_RE.fullmatch(v.strip()):
                    code_cols += 1
                for sn in sheet_names:
                    if sn != ws.title and sn in v:
                        related.add(f"{ws.title}->{sn}")
    wb.close()
    return {
        "pages_or_sheets": len(sheets),
        "sheet_names": ";".join(sheets)[:120],
        "merged_cells": merged_total,
        "multi_header_sheets": multi_header_sheets,
        "hidden_rows_cols": f"{hidden_rows}/{hidden_cols}",
        "formulas": formulas,
        "null_ratio": round((possible - cells) / max(possible, 1), 2),
        "code_values": code_cols,
        "related_sheets": len(related),
        "cells": cells,
    }


def profile(rel: str, doc_type: str) -> dict:
    path = ROOT / rel
    ext = path.suffix.lower()
    if ext == ".pdf":
        feats = profile_pdf(path)
    elif ext == ".docx":
        feats = profile_docx(path)
    elif ext == ".doc":
        feats = profile_doc(path)
    else:
        feats = profile_xlsx(path)
    return feats


def main() -> int:
    rows = []
    for rel, dtype in SAMPLE:
        try:
            f = profile(rel, dtype)
            err = ""
        except Exception as e:
            f, err = {}, f"{type(e).__name__}: {e}"
        import hashlib
        sid = "SRC-" + hashlib.sha1(rel.encode()).hexdigest()[:10].upper()
        row = {"source_id": sid, "relative_path": rel, "format": Path(rel).suffix.lstrip(".").lower(),
               "doc_type": dtype, "parse_issue": err, **{k: v for k, v in f.items() if k != "source_id"}}
        rows.append(row)
        print(f"{sid} [{dtype}] {Path(rel).name}")
        for k, v in row.items():
            if k not in ("source_id", "relative_path", "doc_type", "parse_issue"):
                print(f"    {k}: {v}")
        if err:
            print(f"    !! {err}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k != "source_id", k))
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"\n写入 {OUT_CSV} ({len(rows)} 行)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
