# P00 项目范围与资料治理

## 状态

PASSED（2026-09-03 用户验收）

## 学习目标

- 理解并会执行阶段门管理制度；
- 掌握数据分级与数据治理边界的设定方法；
- 理解 provenance 与 source_id 在删除传播中的作用；
- 学会编写 ADR 和阶段报告。

## 实现任务

1. 建立项目控制文档体系（PROJECT_CHARTER / ROADMAP / KNOWLEDGE_MAP / WORKFLOW / CURRENT_STATUS / DATA_GOVERNANCE / GLOSSARY / TASK_TEMPLATE）；
2. 与用户确认资料目录、格式与安全等级，形成资料清单（docs/reports/P00-data-inventory.md）；
3. 建立问题池（docs/reports/P00-question-pool.md），按 候选 / 可验证 / 跨文档 / 冲突或不可回答 分类；
4. 确认原始资料存放路径（仓库外）并在资料清单登记代号；
5. 建立第一个 ADR 模板实例（docs/decisions/ADR-000-template.md 可选）。

## 可验证产物

- docs/ 全部控制文件存在且内容完整；
- docs/reports/P00-data-inventory.md（含每份资料的等级标注）；
- docs/reports/P00-question-pool.md（问题池初版）；
- CURRENT_STATUS.md 与实际进度一致。

## 测试和指标

- 文档完整性检查：所有必需小节齐全（本文件的检查清单）；
- 资料清单字段完整性：每条记录含 代号 / 格式 / 数量 / 等级 / 用户确认标记；
- 问题池字段完整性：每个问题含 类型标注 和 可验证性标注。

## 通过标准

1. 全部控制文档建立并经用户浏览确认；
2. 资料清单覆盖用户确认的全部资料，等级 100% 标注且经用户确认；
3. 问题池中可验证问题 ≥ 1、跨文档问题 ≥ 1（用于后续阶段验收）；
4. 原始资料路径不出现在仓库任何文件中；
5. CURRENT_STATUS.md 的阻塞项清空或转为新的明确阻塞。

## 未通过时的处理

- 资料范围未确认 → 阻塞项留在 CURRENT_STATUS.md，生成「用户确认清单」任务，不进入 P01；
- 文档不完整 → 登记修复任务，限本阶段内完成；
- 任何阶段都不得以"先做起来"为由跳过本阶段通过标准。

## 进入下一阶段的条件

P00 通过标准全部满足，Codex 出具 P00 阶段报告，CURRENT_STATUS.md 更新为 P01 / IN_PROGRESS。
