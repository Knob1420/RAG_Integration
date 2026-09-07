# P01 数据解析与规范化

## 状态

PASSED（2026-09-07 用户验收通过，报告 docs/reports/P01-phase-report.md）

## 学习通过门（验收时须能解释）

- 为什么 PDF、DOCX、XLSX 不能使用同一个解析策略；
- 为什么 Chunk 必须保留页码、章节、工作表和来源；
- 为什么 filesystem_mtime 不能直接当作版本；
- 为什么扫描 PDF 不能生成空文本进入索引；
- 为什么表格要保留表头、单位和条件。

## 实现任务（拆分为任务包执行）

1. **TASK-P01-001 数据模型 ADR**：Document/Chunk/source_id/content_sha256/主副本口径、chunk 溯源字段（页码/章节/sheet/行列）、解析状态机（NOT_STARTED→PENDING→DONE/FAILED）；
2. **TASK-P01-002 解析管线**：WPS zip 修复层（第一站）+ 分格式解析（docx 标题层级与表格 / xlsx 按 sheet 逻辑区域 / pdf 文本层分流 / doc libreoffice），扫描件标 PENDING 不产空文本；
3. **TASK-P01-003 主副本与判同**：content_sha256 计算、5 组同名文件主副本标记、近重复分组；
4. **TASK-P01-004 元数据预填**：doc_type/subsystem/document_version 等 UNKNOWN 字段按解析结果预填 + 抽样人工确认；
5. **TASK-P01-005 解析质量报告**：抽样人工比对原文与规范化输出，source_id 回链 100% 抽查。

## 通过标准（工程）

- 抽样解析正确率 ≥ 用户与 Codex 约定的阈值（质量报告时定）；
- 所有 Chunk 可回链原始页码/位置；
- parse_status 流转完整，扫描件无一进入索引为空文本；
- pytest 全绿。

## 未通过时的处理

解析缺陷登记修复任务；必要时 ADR 缩小首版格式范围（扫描件 OCR 决策已在 ROADMAP 预留）。
