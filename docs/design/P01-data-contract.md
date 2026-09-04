# P01 数据契约（data contract）

> TASK-P01-002 产物。实现：`src/rag_integration/models.py`（仅标准库）。字段级定义见 `P01-schema.md`。

## 数据流与模型关系

```text
SourceDocument ──→ ParseRun ──→ DocumentElement（含 Location + Provenance）
                     │                │
                     │                └──→ ChunkRecord（P02 消费）
                     └──→ QualityIssue（旁挂，只含计数与判定）
```

| 模型 | 职责 | 谁生产 | 谁消费 |
|------|------|--------|--------|
| SourceDocument | manifest 一行的运行时对象；删除传播主体 | manifest 载入 | 解析管线、P01-003 主副本判定 |
| ParseRun | 一次解析执行（source×解析器版本×路由×时间）；状态机载体 | 解析管线 | P01-005 质量报告 |
| Location | 内容在原文档的位置（页/sheet/章节/行/块） | 解析器 | 溯源回链、稳定 ID |
| Provenance | 谁用什么经哪条路由产出（解析器版本、路由及触发原因） | 解析器 | 质量报告、检索侧按 mode 加权 |
| DocumentElement | 最小可溯源内容单元（段落/标题/表行/键值/图占位/显式省略） | 解析器 | 索引、Chunk |
| ChunkRecord | 检索粒度单元；只引用 element_ids，溯源经 element 传递 | P02 切分 | 索引、Embedding |
| QualityIssue | 质量问题记录；message 不含正文 | 质量检查器 | 人工复核队列、质量报告 |

## 契约规则

1. **构造期校验，宁失败不放行**：非法 source_id、空内容 Element、无锚点 Location、无表头 TABLE_ROW、终态无 finished_at 的 ParseRun——全部在 `__post_init__` 抛 `ValueError`。静默的错比显式失败更危险。
2. **稳定 ID 与内容无关**（element_id）：同位置重解析 ID 不变，文本漂移靠对比同 ID 的前后内容发现（对应质量项 DRIFT_WARNING）。
3. **空文本不得产出**：空页/扫描失败页用 `PAGE_OMITTED` + `page_omitted_reason` 显式省略，禁止空串 Element 入索引。
4. **溯源链完整**：每个 Element 的 `location.source_id` 必须等于自身 `source_id`（构造期校验）；ChunkRecord 不复制溯源字段，经 element_ids 反查。
5. **序列化**：`to_json()`（enum→value、tuple→list、ensure_ascii=False）；`DocumentElement`/`ParseRun` 提供 `from_json` 往返。其余模型按需再加。
6. **质量记录无正文**：QualityIssue 只允许计数、判定、观测值与阈值。

## 状态机（ParseRun.status）

```
NOT_STARTED → IN_PROGRESS → DONE（进索引）
                 ├→ PENDING_OCR → IN_PROGRESS（R3）
                 ├→ PENDING_REVIEW（人工，不进索引）
                 └→ FAILED（不进索引，附原始错误）
```

终态（DONE/PENDING_REVIEW/FAILED）必须带 `finished_at`。

## 不变式清单（测试对应）

| 不变式 | 测试 |
|--------|------|
| RouteId 恰为 R1–R10；ParseStatus 恰 6 态 | test_route_and_status_enums |
| source_id 格式 `SRC-[0-9A-F]{10}`；checksum 64 位小写 hex | test_source_document_rejects |
| Location ≥1 锚点；序号锚点 ≥1；章节链无空串 | test_location_* |
| element_id 确定性且 seq 区分同位多元素 | test_element_stable_id_and_seq |
| TABLE_ROW 必带非空 header；HEADING 必带 level | test_element_table_row/heading |
| PAGE_OMITTED：空串 + 必带原因 | test_element_page_omitted_rules |
| JSON 往返保持 ID 与枚举 | test_element_json_round_trip 等 |
