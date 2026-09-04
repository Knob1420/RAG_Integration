# TASK-P00-004 航天资料候选问题发现

## 状态

ACCEPTED

## 目标

基于 manifest、P00-data-profile.md 和本地航天资料，发现 30～50 个可用于后续 RAG 评测的候选问题。

## GLM Implementation Report

### 修改文件

- `eval/questions/build_pool.py`（40 问数据 + 建池脚本，可复现）
- `eval/questions/question_pool.csv` + `question_cards/Q-001~040.yaml`
- `scripts/validate_question_pool.py` + `tests/test_question_pool.py`
- `docs/reports/P00-question-discovery.md`（完整统计报告）
- 本文件

### 执行的命令及结果

- 锚点提取（本地 python-docx/openpyxl/fitz，未调外部 API，输出未入库）
- `build_pool.py` → 40 问；`validate_question_pool.py` → **校验通过**；`pytest tests/ -q` → **22 passed**

### 关键数字

- 40 问（≥30）：参数/接口/IDS 11、测试/试验/结论 9+、方案/会议 5、跨文档 7、时间/版本 4、冲突/不足/不可答 4（类型字段口径见报告）
- answerable 29 / partially 9 / unanswerable 2；多来源 13；证据位置 40/40
- 全部 review_status=machine_draft，source_id 100% 回链 manifest

### 与任务包的偏差

1. "文档引用"类问题（Q-026）related_source_ids 使用特殊值 `MANIFEST` 表示回链清单整体（校验器放行该值）；
2. 空约束字段显式填 `NONE` 而非留空（校验器要求字段非空）。

### 已知限制

- 证据位置为章节/sheet 级；answerable 为机器初判待用户复核；详见报告"已知限制"。

### 需要决策的问题

1. 用户逐问复核（价值分/可答性）；
2. 2 个扫描件不可答问题是否作为 P01 启用 OCR 的依据；
3. 问题池作为 P03 评测集种子。

## Codex Review

### Review 结果

（待填）

### 发现的问题

（待填）

### 修复任务

（待填）

### 验收状态

（待填）

> 验收记录：2026-09-03 用户确认 P00 验收通过（阶段报告 docs/reports/P00-phase-report.md，复盘记录见 learning/P00-learning-sprint.md）。
