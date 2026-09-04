# P01 模型 Schema（字段级定义）

> TASK-P01-002 产物。实现：`src/rag_integration/models.py`。所有模型 dataclass + `__post_init__` 校验 + `to_json()`。

## 枚举

| 枚举 | 取值 | 用途 |
|------|------|------|
| ParseStatus | NOT_STARTED / IN_PROGRESS / DONE / PENDING_OCR / PENDING_REVIEW / FAILED | 解析状态机 |
| RouteId | R1–R10 | 解析路由（P01-parser-routing.md） |
| ExtractionMode | text_native / text_ocr / mixed_native_ocr / docx_structured / docx_structured_wps / doc_converted / xlsx_structured / pptx_structured | 提取方式，Element 级标注 |
| ElementType | paragraph / heading / table / table_row / key_value / figure / page_omitted | 内容单元类型 |
| DetectionMethod | lattice / stream / ocr_layout / native | 表格来源检测（PDF 三态 + 结构原生） |
| PageType | text / scan / empty | PDF 页级双信号分类 |
| IssueCode | parse_error / text_volume_low / cjk_ratio_low / garbled_char_high / ocr_density_low / table_structure_mismatch / cell_conservation_fail / heading_missing / empty_element / missing_location / drift_warning | 质量问题码（P01-quality-requirements.md 检查项映射） |
| Severity | info / warning / blocking | 严重度；blocking = 阻断进索引 |

## 稳定 ID

| ID | 规则 | 备注 |
|----|------|------|
| source_id | `SRC-<sha1(relative_path)[:10].upper()>` | P00 既有约定 |
| element_id | `EL-<sha1(source_id\|type\|locator_key\|seq)[:12].upper()>` | 与内容无关（漂移检测前提） |
| chunk_id | `CHK-<sha1(source_id\|element_ids\|strategy)[:12].upper()>` | |
| run_id | `RUN-<sha1(source_id\|started_at)[:12].upper()>` | |
| issue_id | `QI-<sha1(run_id\|code\|locator)[:12].upper()>` | 同 run 同位置同问题可去重 |

`locator_key`：Location 各锚点按固定字段序拼 `name=value`，`|` 连接；`section_chain` 拼为 `sec=A/B`。

## Location

| 字段 | 类型 | 约束 |
|------|------|------|
| source_id | str | `^SRC-[0-9A-F]{10}$` |
| page_no | int? | PDF 物理页号，≥1 |
| page_type | PageType? | R2/R3 页级标注 |
| section_chain | tuple[str,...] | 章节链；无空串元素 |
| sheet_name | str? | xlsx 工作表名 |
| table_index / row_no / paragraph_no / block_no / slide_no | int? | 均 ≥1 |

约束：至少一个锚点非空（page_no/section_chain/sheet_name/…），否则溯源链断裂 → ValueError。

## Provenance

| 字段 | 类型 | 约束 |
|------|------|------|
| parser_name / parser_version | str | 非空（如 pymupdf / 1.24.0） |
| route | RouteId | |
| extraction_mode | ExtractionMode | |
| route_reason | str | 非空；路由触发原因，P01-005 输入 |

## SourceDocument

| 字段 | 类型 | 约束 |
|------|------|------|
| source_id | str | 格式同上 |
| file_name / relative_path | str | 相对资料根目录 |
| file_extension | str | 无点小写（pdf/docx/…），禁止前导点 |
| file_size | int | ≥0 |
| checksum_sha256 | str | 64 位小写 hex |
| document_type / document_version | str | 默认 UNKNOWN（P01-004 预填） |
| parse_status | ParseStatus | 默认 NOT_STARTED |

## DocumentElement

| 字段 | 类型 | 约束 |
|------|------|------|
| source_id | str | 必须等于 location.source_id |
| element_type | ElementType | |
| content | str | 非空白；PAGE_OMITTED 例外（必须空串） |
| location | Location | |
| provenance | Provenance | |
| seq | int | ≥0；同 locator 同 type 多元素时区分，进 ID |
| metadata | dict | 按类型必填项见下 |
| element_id | str (init=False) | 稳定 ID，自动计算 |

metadata 必填项：

| element_type | 必填 metadata | 说明 |
|--------------|----------------|------|
| TABLE_ROW | `header: list[str]` 非空 | 进索引硬门槛（行数据须自带表头语义） |
| TABLE_ROW (PDF) | `detection_method` | lattice/stream/ocr_layout |
| HEADING | `level: int` | 标题层级 |
| PAGE_OMITTED | `page_omitted_reason: str` 非空 | empty / signature 豁免等 |

序列化：`to_json()` / `from_json()` 往返（注意 tuple→list）。

## ChunkRecord（P02 消费，本阶段定形）

| 字段 | 类型 | 约束 |
|------|------|------|
| source_id | str | 格式校验 |
| element_ids | tuple[str,...] | 非空；溯源经此传递，不复制字段 |
| content | str | 非空白（空块禁止产出） |
| strategy | str | 切分策略标识（heading_window 等） |
| metadata | dict | |
| chunk_id | str (init=False) | 自动计算 |

## ParseRun

| 字段 | 类型 | 约束 |
|------|------|------|
| source_id / parser_name / parser_version / route / route_reason | | 同上各约束 |
| started_at | str | ISO 8601（UTC 建议） |
| status | ParseStatus | 默认 IN_PROGRESS；终态必须带 finished_at |
| finished_at | str? | |
| element_count | int | |
| stats | dict | 计数与判定（如 scan_page_ratio），**不含正文** |
| run_id | str (init=False) | 自动计算 |

序列化：`to_json()` / `from_json()` 往返。

## QualityIssue

| 字段 | 类型 | 约束 |
|------|------|------|
| source_id / run_id | str | |
| code | IssueCode | |
| severity | Severity | |
| message | str | 非空；**禁止包含正文** |
| observed / threshold | str? | 如 "cjk=0.06" / ">=0.2" |
| locator | str? | locator_key 或人读位置串 |
| issue_id | str (init=False) | 自动计算 |
