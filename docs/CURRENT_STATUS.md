# 当前状态（CURRENT_STATUS）

> 本文件是项目状态的唯一权威视图。每次任务或阶段状态变更时更新。

- **当前阶段**：P00（含 P00-L）已完成，待最终验收 → **P01（下一个）**
- **状态**：P00 PASSED_PENDING_ACCEPTANCE（阶段报告已出：docs/reports/P00-phase-report.md；P00-L 复盘通过）
- **已完成**：
  - 项目控制文件体系（9 文档，TASK-P00-001，含评审修正）
  - 元数据清单 data_manifest.csv：83 条，source_id 稳定无重复（TASK-P00-002）
  - 定级：security_level 全部"内部可用"、external_model_allowed 全部 YES（仅公司模型 API）
  - Manifest 验证：18 字段契约对齐，验证通过无问题（TASK-P00-003A）
  - 数据画像：16 份分层抽样，WPS zip 坑/扫描件/无新依赖三项关键发现（TASK-P00-003B）
  - 问题池：40 问（answerable 29 / partially 9 / unanswerable 2，多来源 13），校验通过（TASK-P00-004）
- **已登记资料**：83（docx 47 / pdf 26 / xlsx 8 / doc 2；存放仓库外 ../Data）
- **候选问题**：40（**21 问正式测评集** user_reviewed：Q-002/003/005/006/007/010/011/014/015/017/018/019/023/028/032/034/035/037/038/039/040，含拒答组 Q-037；其余 19 仍 machine_draft）
- **可验证问题**：29（answerable，待用户复核后转正）
- **跨文档问题**：13（requires_multiple_sources）
- **冲突或不可回答问题**：11（含纯扫描件 2 个不可答）
- **当前阻塞**：无。待 Codex/用户对 P00 阶段报告（docs/reports/P00-phase-report.md）做最终验收。
- **下一步**：P00 验收 → P01 数据解析与规范化。P01 首任务：① 数据模型 ADR（Document/Chunk/source_id/content_sha256/主副本）；② WPS 修复层 + 分格式解析管线；③ 学习通过门（见 P00-phase-report 结论）
- **P00 通过条件**：见 docs/phases/P00-project-scope.md；P00-L 通过条件见 docs/phases/P00-L-learning-bridge.md（复盘已通过）

## 更新日志

| 日期 | 阶段 | 变更 |
|------|------|------|
| 2026-08-31 | P00 | 文件初始化 |
| 2026-09-01 | P00 | 控制文件建立+评审修正；清单 83 条并外迁+mtime 修复；定级完成；003A 验证通过；003B 画像 16 份；004 问题池 40 问 |
| 2026-09-01 | P00-L | 设立学习桥接阶段（用户决策）：docs/learning/ 五件套 + 阶段文件 + ROADMAP/P01 入口条件挂钩 |
| 2026-09-03 | P00-L | 五件套完成（复盘通过，自写/代写边界见 sprint 记录） |
| 2026-09-03 | P00 | 阶段报告出具（docs/reports/P00-phase-report.md），通过条件 5/5 满足，待最终验收 |
