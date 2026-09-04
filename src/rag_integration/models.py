"""TASK-P01-002 统一数据模型与数据契约。

仅标准库（约束：不安装 pydantic）。所有模型满足：
- 构造期校验（非法即抛 ValueError，宁失败不放行）；
- to_json 可序列化（enum→value，tuple→list）；
- 稳定 ID：与内容无关（element_id），重解析可做漂移对比。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional

SOURCE_ID_RE = re.compile(r"^SRC-[0-9A-F]{10}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _h(text: str, n: int) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n].upper()


# ---------------------------------------------------------------- enums

class ParseStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"                    # 质量门全过，允许进索引
    PENDING_OCR = "PENDING_OCR"      # R3 专属中间态，OCR 队列
    PENDING_REVIEW = "PENDING_REVIEW"  # 成功但存疑，人工复核，不进索引
    FAILED = "FAILED"                # 不进索引


class RouteId(str, Enum):
    R1 = "R1"    # 数字版 PDF，文本直提
    R2 = "R2"    # 混合版 PDF，页级分流
    R3 = "R3"    # 扫描版 PDF，MinerU OCR
    R4 = "R4"    # 标准 DOCX
    R5 = "R5"    # WPS 反斜杠 DOCX（先修复再走 R4）
    R6 = "R6"    # 旧 DOC，LibreOffice 转 docx 后走 R4
    R7 = "R7"    # 常规 XLSX
    R8 = "R8"    # 复杂多区 XLSX（多行表头/合并/公式）
    R9 = "R9"    # 不支持格式，只登记不解析
    R10 = "R10"  # PPT/PPTX（预留）


class ExtractionMode(str, Enum):
    TEXT_NATIVE = "text_native"
    TEXT_OCR = "text_ocr"
    MIXED_NATIVE_OCR = "mixed_native_ocr"
    DOCX_STRUCTURED = "docx_structured"
    DOCX_STRUCTURED_WPS = "docx_structured_wps"  # R5：经 WPS 修复
    DOC_CONVERTED = "doc_converted"              # R6：经 LibreOffice 转换链
    XLSX_STRUCTURED = "xlsx_structured"
    PPTX_STRUCTURED = "pptx_structured"


class ElementType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"          # 整表（PDF/DOCX 表格）
    TABLE_ROW = "table_row"  # 行记录（每行自带表头，进索引单元）
    KEY_VALUE = "key_value"  # 元信息区键值对（xlsx 元区等）
    FIGURE = "figure"        # 插图占位（首版不抽内容）
    PAGE_OMITTED = "page_omitted"  # 空页/装饰页/豁免页，显式省略而非空串


class DetectionMethod(str, Enum):
    """表格来源检测方式（PDF 表格三态）。"""
    LATTICE = "lattice"      # 线框表
    STREAM = "stream"        # 无线框表
    OCR_LAYOUT = "ocr_layout"  # MinerU 版面还原表格
    NATIVE = "native"        # docx/xlsx 结构原生表格


class PageType(str, Enum):
    """PDF 页级双信号分类（P01-parser-routing.md）。"""
    TEXT = "text"    # chars>=50
    SCAN = "scan"    # chars<50 且最大图覆盖>=85%
    EMPTY = "empty"  # chars<50 无大图


class IssueCode(str, Enum):
    PARSE_ERROR = "parse_error"
    TEXT_VOLUME_LOW = "text_volume_low"          # 文本量下限
    CJK_RATIO_LOW = "cjk_ratio_low"              # <0.2
    GARBLED_CHAR_HIGH = "garbled_char_high"      # \ufffd 等 >=1%
    OCR_DENSITY_LOW = "ocr_density_low"          # 整页表格页 <50 字符
    TABLE_STRUCTURE_MISMATCH = "table_structure_mismatch"  # 行列守恒
    CELL_CONSERVATION_FAIL = "cell_conservation_fail"      # 单元格守恒
    HEADING_MISSING = "heading_missing"          # 标题层级非空率
    EMPTY_ELEMENT = "empty_element"              # 空文本阻断
    MISSING_LOCATION = "missing_location"        # 溯源缺失
    DRIFT_WARNING = "drift_warning"              # 重跑漂移 >30%/10%


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"  # 阻断进索引


# ---------------------------------------------------------------- mixins

def _json_default(o: Any) -> Any:
    if isinstance(o, Enum):
        return o.value
    raise TypeError(f"not JSON serializable: {type(o)!r}")


class ToJsonMixin:
    def to_dict(self) -> dict:
        return asdict(self)  # type: ignore[arg-type]

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(asdict(self), default=_json_default,
                          ensure_ascii=False, indent=indent)


# ---------------------------------------------------------------- models

@dataclass
class Location(ToJsonMixin):
    """内容在原文档中的位置。至少一个锚点，否则溯源链断裂。"""
    source_id: str
    page_no: Optional[int] = None        # PDF 物理页号，1 起
    page_type: Optional[PageType] = None  # R2/R3 页级标注
    section_chain: tuple[str, ...] = ()  # 章节链 H1/H2/H3
    sheet_name: Optional[str] = None     # xlsx
    table_index: Optional[int] = None    # 文档内表格序号，1 起
    row_no: Optional[int] = None         # 表格/工作表行号，1 起
    paragraph_no: Optional[int] = None   # 段落序
    block_no: Optional[int] = None       # OCR 版面块序号
    slide_no: Optional[int] = None       # pptx 当页用

    def __post_init__(self) -> None:
        if not SOURCE_ID_RE.match(self.source_id):
            raise ValueError(f"bad source_id: {self.source_id!r}")
        anchors = (self.page_no, self.section_chain, self.sheet_name,
                   self.table_index, self.row_no, self.paragraph_no,
                   self.block_no, self.slide_no)
        if all(a is None or a == () for a in anchors):
            raise ValueError("Location needs at least one anchor")
        for a in (self.page_no, self.table_index, self.row_no,
                  self.paragraph_no, self.block_no, self.slide_no):
            if a is not None and a < 1:
                raise ValueError(f"anchor number must be >=1: {a}")
        if any(not s.strip() for s in self.section_chain):
            raise ValueError("section_chain must be non-empty strings")

    @property
    def locator_key(self) -> str:
        """进稳定 ID 的规范串（字段顺序固定）。"""
        parts = [self.source_id]
        for name in ("page_no", "sheet_name", "table_index", "row_no",
                     "paragraph_no", "block_no", "slide_no"):
            v = getattr(self, name)
            if v is not None:
                parts.append(f"{name}={v}")
        if self.section_chain:
            parts.append("sec=" + "/".join(self.section_chain))
        return "|".join(parts)


@dataclass
class Provenance(ToJsonMixin):
    """谁、用什么、经哪条路由产出该 Element。"""
    parser_name: str
    parser_version: str
    route: RouteId
    extraction_mode: ExtractionMode
    route_reason: str  # 路由触发原因（P01-005 质量报告输入）

    def __post_init__(self) -> None:
        if not self.parser_name or not self.parser_version:
            raise ValueError("parser_name/parser_version required")
        if not self.route_reason:
            raise ValueError("route_reason required")


@dataclass
class SourceDocument(ToJsonMixin):
    """manifest 一行的运行时对象。"""
    source_id: str
    file_name: str
    relative_path: str
    file_extension: str  # 无点小写，如 pdf/docx
    file_size: int
    checksum_sha256: str
    document_type: str = "UNKNOWN"
    document_version: str = "UNKNOWN"
    parse_status: ParseStatus = ParseStatus.NOT_STARTED

    def __post_init__(self) -> None:
        if not SOURCE_ID_RE.match(self.source_id):
            raise ValueError(f"bad source_id: {self.source_id!r}")
        if not SHA256_RE.match(self.checksum_sha256):
            raise ValueError(f"bad checksum_sha256: {self.checksum_sha256!r}")
        if self.file_size < 0:
            raise ValueError("file_size must be >=0")
        if self.file_extension.startswith("."):
            raise ValueError("file_extension without leading dot")


@dataclass
class DocumentElement(ToJsonMixin):
    """最小可溯源内容单元。content 非空（PAGE_OMITTED 除外，须带省略原因）。"""
    source_id: str
    element_type: ElementType
    content: str
    location: Location
    provenance: Provenance
    seq: int = 0  # 同 locator 同 type 多个 Element 时的序，进稳定 ID
    metadata: dict = field(default_factory=dict)  # header/detection_method/page_omitted_reason 等
    element_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.element_type == ElementType.PAGE_OMITTED:
            if self.content != "":
                raise ValueError("PAGE_OMITTED content must be empty string")
            if not self.metadata.get("page_omitted_reason"):
                raise ValueError("PAGE_OMITTED requires page_omitted_reason")
        elif not self.content.strip():
            raise ValueError("content must be non-empty")
        if self.element_type == ElementType.TABLE_ROW:
            header = self.metadata.get("header")
            if not isinstance(header, (list, tuple)) or not header:
                raise ValueError("TABLE_ROW requires non-empty header")  # 进索引硬门槛
        if self.element_type == ElementType.HEADING:
            if not self.metadata.get("level"):
                raise ValueError("HEADING requires level")
        if self.location.source_id != self.source_id:
            raise ValueError("location.source_id mismatch")
        if self.seq < 0:
            raise ValueError("seq must be >=0")
        self.element_id = "EL-" + _h(
            f"{self.source_id}|{self.element_type.value}|"
            f"{self.location.locator_key}|{self.seq}", 12)

    @classmethod
    def from_dict(cls, d: dict) -> "DocumentElement":
        loc = Location(**d["location"])
        prov = Provenance(
            parser_name=d["provenance"]["parser_name"],
            parser_version=d["provenance"]["parser_version"],
            route=RouteId(d["provenance"]["route"]),
            extraction_mode=ExtractionMode(d["provenance"]["extraction_mode"]),
            route_reason=d["provenance"]["route_reason"],
        )
        return cls(
            source_id=d["source_id"],
            element_type=ElementType(d["element_type"]),
            content=d["content"],
            location=loc,
            provenance=prov,
            seq=d.get("seq", 0),
            metadata=d.get("metadata") or {},
        )

    @classmethod
    def from_json(cls, s: str) -> "DocumentElement":
        return cls.from_dict(json.loads(s))


@dataclass
class ChunkRecord(ToJsonMixin):
    """检索单元（P02 消费，本任务只定形）。溯源经 element_ids 传递，不复制字段。"""
    source_id: str
    element_ids: tuple[str, ...]
    content: str
    strategy: str  # 切分策略标识，如 "element_per_chunk"/"heading_window"
    metadata: dict = field(default_factory=dict)
    chunk_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not SOURCE_ID_RE.match(self.source_id):
            raise ValueError(f"bad source_id: {self.source_id!r}")
        if not self.element_ids:
            raise ValueError("element_ids required")
        if not self.content.strip():
            raise ValueError("content must be non-empty")
        if not self.strategy:
            raise ValueError("strategy required")
        self.chunk_id = "CHK-" + _h(
            f"{self.source_id}|{','.join(self.element_ids)}|{self.strategy}", 12)


@dataclass
class ParseRun(ToJsonMixin):
    """一次解析执行：source × 解析器版本 × 路由 × 时间。状态机载体。"""
    source_id: str
    parser_name: str
    parser_version: str
    route: RouteId
    route_reason: str
    started_at: str  # ISO 8601 UTC
    status: ParseStatus = ParseStatus.IN_PROGRESS
    finished_at: Optional[str] = None
    element_count: int = 0
    stats: dict = field(default_factory=dict)  # 计数与判定，不含正文
    run_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not SOURCE_ID_RE.match(self.source_id):
            raise ValueError(f"bad source_id: {self.source_id!r}")
        if not self.parser_name or not self.parser_version:
            raise ValueError("parser_name/parser_version required")
        if not self.route_reason:
            raise ValueError("route_reason required")
        if self.status not in (ParseStatus.NOT_STARTED, ParseStatus.IN_PROGRESS,
                               ParseStatus.PENDING_OCR) and self.finished_at is None:
            raise ValueError(f"terminal status {self.status} requires finished_at")
        self.run_id = "RUN-" + _h(f"{self.source_id}|{self.started_at}", 12)

    @classmethod
    def from_dict(cls, d: dict) -> "ParseRun":
        return cls(
            source_id=d["source_id"],
            parser_name=d["parser_name"],
            parser_version=d["parser_version"],
            route=RouteId(d["route"]),
            route_reason=d["route_reason"],
            started_at=d["started_at"],
            status=ParseStatus(d["status"]),
            finished_at=d.get("finished_at"),
            element_count=d.get("element_count", 0),
            stats=d.get("stats") or {},
        )

    @classmethod
    def from_json(cls, s: str) -> "ParseRun":
        return cls.from_dict(json.loads(s))


@dataclass
class QualityIssue(ToJsonMixin):
    """质量问题记录。message 只含计数与判定，不含正文（治理红线）。"""
    source_id: str
    run_id: str
    code: IssueCode
    severity: Severity
    message: str
    observed: Optional[str] = None   # 如 "cjk_ratio=0.06"
    threshold: Optional[str] = None  # 如 ">=0.2"
    locator: Optional[str] = None    # Location.locator_key 或人读位置串
    issue_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not SOURCE_ID_RE.match(self.source_id):
            raise ValueError(f"bad source_id: {self.source_id!r}")
        if not self.message:
            raise ValueError("message required")
        self.issue_id = "QI-" + _h(
            f"{self.run_id}|{self.code.value}|{self.locator or ''}", 12)
