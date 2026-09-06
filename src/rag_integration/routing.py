"""TASK-P01-FULL-PIPELINE: 解析路由判定（P01-parser-routing.md 的 R1-R10）。"""
from __future__ import annotations

from .models import PageType, RouteId
from .probe import SUPPORTED_EXTS, ProbeResult


def decide(pr: ProbeResult) -> tuple[RouteId, str]:
    """返回 (路由, 触发原因)。原因进 Provenance.route_reason 与质量报告。"""
    if pr.error:
        return RouteId.R9, f"probe_failed: {pr.error}"

    if pr.ext not in SUPPORTED_EXTS:
        return RouteId.R9, f"unsupported ext: {pr.ext}"

    if pr.ext == "pdf":
        n = len(pr.page_types)
        text = sum(t is PageType.TEXT for t in pr.page_types)
        scan = sum(t is PageType.SCAN for t in pr.page_types)
        if scan == 0:
            return RouteId.R1, f"{n}/{n} text pages"
        if scan / n > 0.5:
            return RouteId.R3, f"{scan}/{n} scan pages (>50%)"
        return RouteId.R2, f"mixed: {text} text + {scan} scan / {n}"

    if pr.ext == "docx":
        if pr.wps_backslash:
            return RouteId.R5, "zip entries contain backslash (WPS)"
        return RouteId.R4, "standard docx zip entries"

    if pr.ext == "doc":
        return RouteId.R6, "legacy binary doc -> libreoffice -> R4"

    if pr.ext == "xlsx":
        if pr.xlsx_complex_reasons:
            return RouteId.R8, "complex: " + ", ".join(pr.xlsx_complex_reasons)
        return RouteId.R7, "regular sheet form"

    if pr.ext in ("ppt", "pptx"):
        return RouteId.R10, "reserved: no ppt in corpus yet"

    return RouteId.R9, f"unhandled ext: {pr.ext}"  # pragma: no cover
