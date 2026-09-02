# P00 候选问题发现报告（TASK-P00-004）

日期：2026-09-01 · 方法：本地锚点提取（标题/编号节/表头/结论句/版本表）→ 人工建池，未调用任何外部模型 API
产物：`eval/questions/question_pool.csv` + `eval/questions/question_cards/Q-001~040.yaml` + `eval/questions/build_pool.py`（可复现重建）

## 统计

- **候选问题总数：40**（要求 ≥30）
- **各类型**：parameter_lookup 8 · interface_lookup 3 · test_result_lookup 9 · design_decision_lookup 2 · meeting_action_lookup 3 · cross_document_trace 7 · time_or_version_compare 4 · conflict_detection 1 · insufficient_evidence 3（另：document_discovery 0，类型预留）
- **可回答性**：answerable 29 · partially_answerable 9 · unanswerable 2（部分+不可答 11 ≥ 3）
- **跨文档**：requires_multiple_sources 13（≥5）；cross_document_trace 类 7
- **证据明确**：40/40 有真实 source_id + 证据位置（≥20）
- review_status 全部 machine_draft，待用户复核

## 最高价值问题（value_score=3 代表）

- Q-011/012 验收级随机振动/热真空试验结论（验收追溯核心）
- Q-017 GPU 板问题定位与交叉验证（故障归零链）
- Q-026 总结报告引用文件 → manifest 回链（追溯图种子）
- Q-028 程控时间表 8.31 vs 9.2 变化比对（增量更新场景）
- Q-032 试验大纲 ↔ 总结报告执行闭环（覆盖缺口检测）
- Q-035 程控时间表 mtime 序列 vs 内容演进（版本线索有效性检验）

## 当前无法判断价值的问题（需用户复核）

- Q-010 导热硅脂用量、Q-024 EEPROM 用途（业务价值取决于使用场景）
- Q-004/Q-036 文件编号类（价值取决于编号体系是否纳入精确检索）

## 发现的资料冲突/缺口

1. **扫描件证据真空**：《（硬件）验收测试记录表》三份近重复扫描件无文本层（Q-020/Q-037 不可答，前置条件=OCR）；
2. **建议→设计未闭环**：会议建议（CPU 4核）与总体设计方案器件表能否互相判定存疑（Q-040，证据不足型冲突）；
3. **遗留无结论**：GPU 子卡问题原厂分析短期无结论（Q-039）；
4. **大纲↔执行可能存在缺口**：需逐项比对（Q-032）；
5. **mtime 弱版本线索**：程控时间表 4 份仅靠 mtime 排序，与表内时间演进是否吻合待验（Q-035）。

## 修改文件

- `eval/questions/build_pool.py`（新增，含 40 问数据与 SID 表）
- `eval/questions/question_pool.csv`、`eval/questions/question_cards/Q-*.yaml`（40 张）
- `scripts/validate_question_pool.py`（新增校验器）
- `tests/test_question_pool.py`（新增 3 用例）
- 本报告、任务包 `docs/tasks/active/TASK-P00-004-question-discovery.md`

## 测试命令及结果

- `python eval/questions/build_pool.py` → 40 问 + 40 卡
- `python scripts/validate_question_pool.py` → **校验通过**（配额 40/40/13/11 全达标，source_id 100% 回链 manifest）
- `pytest tests/ -q` → **22 passed**（新增 3）

## 已知限制

1. 证据位置为章节/sheet 级，页码/行号级定位待 P01 解析后细化；
2. answerable 判定为机器初判（基于锚点提取可见性），用户复核时可改；
3. 计算模块 IDS（SRC-F8E406DD21）锚点取自电源模块 IDS 的同构结构推断，P01 需实测核对；
4. 3 个测试覆盖性/证明书类问题的证据行位置引用表头级。

## 需要用户确认的问题

1. 逐问复核价值分与可答性（review_status: machine_draft → user_confirmed/rejected）；
2. 不可答的 2 问（扫描件）是否作为 P01 启用 OCR 的依据之一；
3. 问题池是否作为 P03 评测集的种子（建议是）。
