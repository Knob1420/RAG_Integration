"""TASK-P01-002 模型契约测试。内容全部为合成样例，不含真实资料正文。"""
import pytest

from rag_integration.models import (
    DetectionMethod, DocumentElement, ElementType, ExtractionMode, IssueCode,
    Location, ParseRun, ParseStatus, Provenance, QualityIssue, RouteId,
    Severity, SourceDocument, ChunkRecord,
)

# 合成样例常量
SID = "SRC-0123456789"
SHA = "a" * 64
LOC = Location(source_id=SID, page_no=3, section_chain=("概述", "背景"))
PROV = Provenance(parser_name="pymupdf", parser_version="1.24.0",
                  route=RouteId.R1, extraction_mode=ExtractionMode.TEXT_NATIVE,
                  route_reason="all pages chars>=50")


def make_element(**kw) -> DocumentElement:
    args = dict(source_id=SID, element_type=ElementType.PARAGRAPH,
                content="合成测试内容。", location=LOC, provenance=PROV)
    args.update(kw)
    return DocumentElement(**args)


# ---------------------------------------------------------------- 枚举完备性

def test_route_and_status_enums():
    assert [r.name for r in RouteId] == [f"R{i}" for i in range(1, 11)]
    assert len(ParseStatus) == 6
    assert {s.name for s in ParseStatus} == {
        "NOT_STARTED", "IN_PROGRESS", "DONE", "PENDING_OCR", "PENDING_REVIEW", "FAILED"}
    assert len(DetectionMethod) == 4  # lattice/stream/ocr_layout/native


# ---------------------------------------------------------------- SourceDocument

def test_source_document_ok():
    doc = SourceDocument(source_id=SID, file_name="a.pdf", relative_path="a.pdf",
                         file_extension="pdf", file_size=100, checksum_sha256=SHA)
    assert doc.parse_status is ParseStatus.NOT_STARTED


@pytest.mark.parametrize("kw", [
    dict(source_id="SRC-abc"),            # 非 10 位大写十六进制
    dict(checksum_sha256="xyz"),          # 非 sha256
    dict(file_extension=".pdf"),          # 不带点
    dict(file_size=-1),
])
def test_source_document_rejects(kw):
    base = dict(source_id=SID, file_name="a.pdf", relative_path="a.pdf",
                file_extension="pdf", file_size=100, checksum_sha256=SHA)
    base.update(kw)
    with pytest.raises(ValueError):
        SourceDocument(**base)


# ---------------------------------------------------------------- Location

def test_location_requires_anchor():
    with pytest.raises(ValueError):
        Location(source_id=SID)


def test_location_rejects_zero_page_and_blank_section():
    with pytest.raises(ValueError):
        Location(source_id=SID, page_no=0)
    with pytest.raises(ValueError):
        Location(source_id=SID, section_chain=("",))


def test_locator_key_stable_order():
    a = Location(source_id=SID, page_no=3, sheet_name=None, row_no=5)
    b = Location(source_id=SID, row_no=5, page_no=3)  # 构造顺序不同
    assert a.locator_key == b.locator_key


# ---------------------------------------------------------------- DocumentElement

def test_element_stable_id_and_seq():
    e1, e2 = make_element(), make_element(seq=1)
    assert e1.element_id.startswith("EL-") and len(e1.element_id) == 15
    assert e1.element_id != e2.element_id
    assert make_element().element_id == e1.element_id  # 确定性


def test_element_rejects_empty_content():
    with pytest.raises(ValueError):
        make_element(content="   ")


def test_element_page_omitted_rules():
    ok = make_element(element_type=ElementType.PAGE_OMITTED, content="",
                      metadata={"page_omitted_reason": "empty_page"})
    assert ok.element_id
    with pytest.raises(ValueError):  # 无原因
        make_element(element_type=ElementType.PAGE_OMITTED, content="",
                     metadata={"page_omitted_reason": ""})
    with pytest.raises(ValueError):  # 带内容
        make_element(element_type=ElementType.PAGE_OMITTED, content="x",
                     metadata={"page_omitted_reason": "empty_page"})


def test_element_table_row_requires_header():
    kw = dict(element_type=ElementType.TABLE_ROW,
              location=Location(source_id=SID, page_no=3, table_index=1, row_no=2),
              metadata={"header": ["参数", "值"]})
    assert make_element(**kw).element_id
    with pytest.raises(ValueError):
        make_element(element_type=ElementType.TABLE_ROW,
                     location=Location(source_id=SID, page_no=3, table_index=1, row_no=2),
                     metadata={})
    with pytest.raises(ValueError):
        make_element(element_type=ElementType.TABLE_ROW,
                     location=Location(source_id=SID, page_no=3, table_index=1, row_no=2),
                     metadata={"header": []})


def test_element_heading_requires_level():
    with pytest.raises(ValueError):
        make_element(element_type=ElementType.HEADING, metadata={})
    assert make_element(element_type=ElementType.HEADING,
                        metadata={"level": 1}).element_id


def test_element_source_id_mismatch():
    bad_loc = Location(source_id="SRC-9999999999", page_no=1)
    with pytest.raises(ValueError):
        make_element(location=bad_loc)


def test_element_json_round_trip():
    e = make_element(element_type=ElementType.TABLE_ROW,
                     location=Location(source_id=SID, page_no=3, table_index=1,
                                       row_no=2, section_chain=("附表",)),
                     metadata={"header": ["指令码", "含义"],
                               "detection_method": DetectionMethod.LATTICE.value},
                     seq=3)
    e2 = DocumentElement.from_json(e.to_json())
    assert e2.element_id == e.element_id
    assert e2.element_type is ElementType.TABLE_ROW
    assert list(e2.location.section_chain) == ["附表"]  # json 往返 tuple→list
    assert e2.provenance.route is RouteId.R1
    assert e2.metadata["header"] == ["指令码", "含义"]


# ---------------------------------------------------------------- Provenance / ParseRun

def test_provenance_requires_reason():
    with pytest.raises(ValueError):
        Provenance(parser_name="x", parser_version="1", route=RouteId.R3,
                   extraction_mode=ExtractionMode.TEXT_OCR, route_reason="")


def test_parse_run_lifecycle_and_json():
    run = ParseRun(source_id=SID, parser_name="mineru", parser_version="2.0",
                   route=RouteId.R3, route_reason="8/8 scan pages",
                   started_at="2026-09-04T08:00:00+00:00")
    assert run.status is ParseStatus.IN_PROGRESS
    run.status = ParseStatus.DONE
    run.finished_at = "2026-09-04T08:01:00+00:00"
    run2 = ParseRun.from_json(run.to_json())
    assert run2.run_id == run.run_id and run2.status is ParseStatus.DONE


def test_parse_run_terminal_requires_finished_at():
    with pytest.raises(ValueError):
        ParseRun(source_id=SID, parser_name="p", parser_version="1",
                 route=RouteId.R1, route_reason="r",
                 started_at="2026-09-04T08:00:00+00:00", status=ParseStatus.FAILED)


# ---------------------------------------------------------------- ChunkRecord / QualityIssue

def test_chunk_record_rules():
    c = ChunkRecord(source_id=SID, element_ids=("EL-AAA", "EL-BBB"),
                    content="合成块。", strategy="heading_window")
    assert c.chunk_id.startswith("CHK-")
    with pytest.raises(ValueError):
        ChunkRecord(source_id=SID, element_ids=(), content="x", strategy="s")
    with pytest.raises(ValueError):
        ChunkRecord(source_id=SID, element_ids=("EL-A",), content="", strategy="s")


def test_quality_issue_id_dedup():
    kw = dict(source_id=SID, code=IssueCode.CJK_RATIO_LOW, severity=Severity.BLOCKING,
              message="cjk_ratio below gate", observed="cjk=0.06", threshold=">=0.2")
    run_id = "RUN-000000000AAA"
    q1 = QualityIssue(run_id=run_id, locator="page=5", **kw)
    q2 = QualityIssue(run_id=run_id, locator="page=5", **kw)
    assert q1.issue_id == q2.issue_id  # 同 run 同位置同问题可去重
    q3 = QualityIssue(run_id=run_id, locator="page=6", **kw)
    assert q3.issue_id != q1.issue_id


def test_json_no_raw_content_in_issue():
    q = QualityIssue(source_id=SID, run_id="RUN-000000000AAA",
                     code=IssueCode.TEXT_VOLUME_LOW, severity=Severity.WARNING,
                     message="page chars=12", observed="12", threshold=">=50")
    assert "content" not in q.to_json()
