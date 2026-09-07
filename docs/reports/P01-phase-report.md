# P01 阶段报告：数据解析与规范化

> 2026-09-07 用户验收通过，P01 收口。阶段目标：83 份航天工程资料 → 统一、可溯源、过质量门的检索就绪数据。

## 任务完成情况

| 任务 | 内容 | 结果 |
|---|---|---|
| P01-001 | 解析路由设计（R1-R10/页分类/质量要求/Golden Sample） | ACCEPTED 2026-09-04 |
| P01-002 | 统一数据模型（7 模型+8 枚举，仅标准库） | ACCEPTED 2026-09-04 |
| P01-FULL-PIPELINE | 完整解析管线+全量解析 | ACCEPTED 2026-09-06 |
| P01-003 | 主副本判定（12 从本不进索引） | ACCEPTED 2026-09-07 |
| P01-004 | 元数据预填（类型/子系统/版本族） | ACCEPTED 2026-09-07 |

## 交付物

- **管线**：probe/routing/4 解析器（pdf/docx/doc/xlsx）+ MinerU OCR + quality 五门 + chunking + pipeline 编排，10 模块，57 项测试
- **数据**（仓库外 `Data/derived/p01/`）：17162 Element / 7812 Chunk / 747 条运行历史；**83/83 DONE，0 FAILED**
- **manifest**：20 字段——parse_status 全终态、duplicate_of 主从标记、doc_family/effective_version 版本族、doc_type 73/83、subsystem 67/83（UNKNOWN 残留为过程性文档，用户接受）
- **报告**：解析质量报告、主副本处置表、元数据预填清单、Golden Sample 对照

## 质量门最终状态

cjk 双口径 83/83 过；乱码 0；xlsx 单元格守恒 8/8；无空文本元素（11 空页显式省略）；溯源字段 100%；漂移门实战验证 1 次（xlsx 表头修复触发，正确拦截后确认归零）。OCR 抽检 5 条 warning（编号不在 OCR 区，人工确认非阻断）。

## 验收走查中修复的 6 个实况问题

R3 标题缺失 / xlsx 合并标题行污染表头 / xlsx 内嵌图静默丢失 / docx 封面表误产 / 表题行四格式拉齐 / 漂移门首战验证。全部记入质量报告校准记录。

## 索引就绪规模

71 份（83 − 12 从副本），含 3 版本族 9 份（全版本保留）。

## 转入 P02 的已知缺口（不阻断，按需启用）

1. stream 表检测（无线框 PDF 表）——首版 lattice-only；
2. 无书签 PDF 章节链为空（22 份）——字体推断标题可后补，层结构已预留（补 heading 只影响 chunk 重切）；
3. pdf 原生路合并格不展开（空串占位）；docx/pdf 多行表头无展平（xlsx 独有）；
4. 盖章 PDF 导出仅 3 份达等价线标从，其余（如说明书 docx V1.0 vs 盖章 pdf 12K 字）内容实质不同版本，双方保留；
5. PPT（R10）预留，语料无。

## P02 入口条件核验

- 71 份过门数据 + 元数据过滤维度（type/subsystem/family/version）✓
- 溯源链 chunk→element→location→原文件 ✓
- 问题池 21 问测评集待用 ✓
