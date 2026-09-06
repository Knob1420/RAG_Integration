"""quality 门 + chunking 合成样例测试。"""
from rag_integration.chunking import make_chunks
from rag_integration.models import DocumentElement, ElementType, Location, \
    ParseStatus, Provenance, RouteId, ExtractionMode
from rag_integration.quality import check

SID = "SRC-0123456789"
RUN = "RUN-000000000001"
PROV = Provenance("p", "1", RouteId.R1, ExtractionMode.TEXT_NATIVE, "r")
LOC = Location(SID, page_no=1)


def el(content, etype=ElementType.PARAGRAPH, **kw):
    return DocumentElement(source_id=SID, element_type=etype, content=content,
                           location=kw.pop("location", LOC),
                           provenance=kw.pop("provenance", PROV), **kw)


def test_check_pass_and_cjk_block():
    els = [el("中文内容占比正常的合成测试文本，用于质量门检查。")]
    qr = check(els, SID, RUN, RouteId.R1)
    assert qr.status is ParseStatus.DONE and not qr.issues
    assert len(qr.stats["content_sha256"]) == 64

    bad = [el("latin only garbled " + "\ufffd" * 20)]
    qr2 = check(bad, SID, RUN, RouteId.R1)
    codes = {i.code.value for i in qr2.issues}
    assert qr2.status is ParseStatus.PENDING_REVIEW
    assert "cjk_ratio_low" in codes and "garbled_char_high" in codes

    # 表格主导文档：数字稀释 raw，但字母口径达标 → 放行（全量实测校准）
    table_doc = [el("序号 指令码 含义" + " 加电自检 12.5 0x1F 正常" * 50)]
    qr3 = check(table_doc, SID, RUN, RouteId.R8)
    assert qr3.status is ParseStatus.DONE


def test_check_xlsx_conservation_and_drift():
    els = [el("中文内容正常的表格解析检查文本。")]
    qr = check(els, SID, RUN, RouteId.R8,
               xlsx_stats={"input_cells": 100, "output_cells": 90})
    assert qr.status is ParseStatus.PENDING_REVIEW
    assert any(i.code.value == "cell_conservation_fail" for i in qr.issues)

    qr2 = check(els, SID, RUN, RouteId.R8, prev_stats={"chars": 10})
    assert qr2.status is ParseStatus.PENDING_REVIEW
    assert any(i.code.value == "drift_warning" for i in qr2.issues)


def test_chunks_typed():
    els = [
        el("第一章", ElementType.HEADING, metadata={"level": 1}),
        el("段落一内容。"),
        el("参数 | 值", ElementType.TABLE_ROW,
           metadata={"header": ["参数", "值"]}),
        el("任务代号: X100", ElementType.KEY_VALUE),
        el("第二章", ElementType.HEADING, metadata={"level": 1}),
        el("段落二内容。"),
        el("", ElementType.PAGE_OMITTED,
           metadata={"page_omitted_reason": "empty_page"}),
    ]
    chunks = make_chunks(els, SID)
    strategies = [c.strategy for c in chunks]
    assert strategies == ["heading_window", "table_row", "key_value",
                          "heading_window"]
    assert all(c.chunk_id.startswith("CHK-") for c in chunks)
    assert chunks[1].metadata["header"] == ["参数", "值"]


def test_chunk_window_split_on_size():
    els = [el("第一章", ElementType.HEADING, metadata={"level": 1})]
    els += [el("长内容" * 40) for _ in range(10)]  # 远超 800 字 → 多窗
    chunks = make_chunks(els, SID)
    assert len([c for c in chunks if c.strategy == "heading_window"]) > 1
    assert all(len(c.content) >= 800 / 2 for c in chunks)  # 无碎块
