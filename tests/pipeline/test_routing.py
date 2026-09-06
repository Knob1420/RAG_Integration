"""路由判定纯逻辑测试（无文件 IO，ProbeResult 直接构造）。"""
from pathlib import Path

from rag_integration.models import PageType, RouteId
from rag_integration.probe import ProbeResult
from rag_integration.routing import decide

P = Path("x")


def pr(**kw):
    base = dict(path=P, ext="pdf")
    base.update(kw)
    return ProbeResult(**base)


def test_pdf_routes():
    assert decide(pr(page_types=[PageType.TEXT] * 3))[0] is RouteId.R1
    assert decide(pr(page_types=[PageType.SCAN] * 8))[0] is RouteId.R3
    assert decide(pr(page_types=[PageType.TEXT] * 8 + [PageType.SCAN]))[0] is RouteId.R2
    # 扫描页刚过半 → R3
    assert decide(pr(page_types=[PageType.TEXT] * 4 + [PageType.SCAN] * 5))[0] is RouteId.R3
    # 空页不参与扫描判定：全空 → R1（无扫描页）
    assert decide(pr(page_types=[PageType.EMPTY] * 3))[0] is RouteId.R1


def test_office_routes():
    assert decide(pr(ext="docx")) == (RouteId.R4, "standard docx zip entries")
    assert decide(pr(ext="docx", wps_backslash=True))[0] is RouteId.R5
    assert decide(pr(ext="doc"))[0] is RouteId.R6
    assert decide(pr(ext="xlsx"))[0] is RouteId.R7
    assert decide(pr(ext="xlsx", xlsx_complex_reasons=["merged=3"]))[0] is RouteId.R8
    assert decide(pr(ext="pptx"))[0] is RouteId.R10


def test_r9_and_probe_error():
    assert decide(pr(ext="zip"))[0] is RouteId.R9
    assert decide(pr(ext="txt"))[0] is RouteId.R9
    r, reason = decide(pr(error="BadZipFile: file is not a zip"))
    assert r is RouteId.R9 and "probe_failed" in reason
