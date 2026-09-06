"""TASK-P01-FULL-PIPELINE: 解析质量门（P01-quality-requirements.md 检查项）。

检查产出 QualityIssue + 终态判定（DONE / PENDING_REVIEW）。
FAILED 由管线在解析器抛异常时直接定，本模块不产 FAILED。
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .models import (DocumentElement, ElementType, IssueCode, ParseStatus,
                     QualityIssue, RouteId, Severity)

CODE_RE = re.compile(r"\b[A-Z]{2,}[-/]\d{2,}[A-Z0-9/-]*\b")  # SCS-01 / Z0102 编号
CJK_MIN = 0.2
GARBLED_MAX = 0.01
DRIFT_WARN = 0.30
OCR_DENSITY_MIN = 50


@dataclass
class QualityReport:
    status: ParseStatus = ParseStatus.DONE
    issues: list[QualityIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)  # 计数与判定，无正文


def check(elements: list[DocumentElement], source_id: str, run_id: str,
          route: RouteId, *, xlsx_stats: dict | None = None,
          prev_stats: dict | None = None) -> QualityReport:
    """全量检查 → 终态。宁挂起不放行：任一门不过即 PENDING_REVIEW。"""
    qr = QualityReport()
    text = "\n".join(e.content for e in elements if e.element_type is not
                     ElementType.PAGE_OMITTED)
    chars = len(text)
    cjk_abs = sum("\u4e00" <= c <= "\u9fff" for c in text)
    cjk = cjk_abs / max(chars, 1)
    latin = sum("a" <= c <= "z" or "A" <= c <= "Z" for c in text)
    cjk_letters = cjk_abs / max(cjk_abs + latin, 1)
    garbled = text.count("\ufffd") / max(chars, 1)
    qr.stats = {
        "elements": len(elements),
        "chars": chars,
        "cjk_ratio": round(cjk, 4),
        "cjk_over_letters": round(cjk_letters, 4),
        "garbled_ratio": round(garbled, 4),
        # 硬门槛 6：content_sha256（P01-003 主副本判定输入）
        "content_sha256": hashlib.sha256(
            "\n".join(sorted(e.content for e in elements)).encode("utf-8")
        ).hexdigest(),
    }
    review = False

    def issue(code: IssueCode, sev: Severity, msg: str, observed=None,
              threshold=None):
        qr.issues.append(QualityIssue(
            source_id=source_id, run_id=run_id, code=code, severity=sev,
            message=msg, observed=observed, threshold=threshold))

    # 校准：表格主导文档数字稀释分母（全量实测 letters 口径 0.29-0.71）。
    # 防的失效模式（antiword 丢中文 raw≈0.06）两口径皆低 → 任一达标即过。
    if chars and cjk < CJK_MIN and cjk_letters < CJK_MIN:
        review = True
        issue(IssueCode.CJK_RATIO_LOW, Severity.BLOCKING,
              "cjk_ratio below gate (both raw and letters-only)",
              f"raw={cjk:.3f},letters={cjk_letters:.3f}", f">={CJK_MIN}")
    if garbled >= GARBLED_MAX:
        review = True
        issue(IssueCode.GARBLED_CHAR_HIGH, Severity.BLOCKING,
              "garbled char ratio high", f"{garbled:.3f}", f"<{GARBLED_MAX}")

    if route in (RouteId.R3, RouteId.R2):  # OCR 五门
        ocr_els = [e for e in elements
                   if e.provenance.extraction_mode.value == "text_ocr"]
        pages: dict[int, int] = {}
        for e in ocr_els:
            pages[e.location.page_no] = pages.get(e.location.page_no, 0) + len(e.content)
        thin = [p for p, n in pages.items() if 0 < n < OCR_DENSITY_MIN]
        if thin:
            review = True
            issue(IssueCode.OCR_DENSITY_LOW, Severity.BLOCKING,
                  "ocr page below density floor (missed content?)",
                  f"pages={thin}", f">={OCR_DENSITY_MIN} chars")
        ocr_text = "\n".join(e.content for e in ocr_els)
        if ocr_text and not CODE_RE.search(ocr_text):
            issue(IssueCode.TEXT_VOLUME_LOW, Severity.WARNING,
                  "no code-like tokens in ocr text (spot check)")

    if xlsx_stats and xlsx_stats["input_cells"] != xlsx_stats["output_cells"]:
        review = True
        issue(IssueCode.CELL_CONSERVATION_FAIL, Severity.BLOCKING,
              "cell conservation mismatch",
              f"in={xlsx_stats['input_cells']}",
              f"out={xlsx_stats['output_cells']}")

    if prev_stats and prev_stats.get("chars"):
        drift = abs(chars - prev_stats["chars"]) / prev_stats["chars"]
        qr.stats["drift_vs_prev"] = round(drift, 4)
        if drift > DRIFT_WARN:
            review = True
            issue(IssueCode.DRIFT_WARNING, Severity.BLOCKING,
                  "text volume drift vs previous run",
                  f"{drift:.2f}", f"<={DRIFT_WARN}")

    qr.status = ParseStatus.PENDING_REVIEW if review else ParseStatus.DONE
    return qr
