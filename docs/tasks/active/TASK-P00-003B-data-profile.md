# TASK-P00-003B 航天资料结构抽样与数据画像

## 状态

IMPLEMENTED

## 目标

从 X100 资料中按格式和文档类型分层抽样，分析后续解析、切分和检索所需的数据结构。

## GLM Implementation Report

### 修改文件

- `scripts/profile_sample.py`（新增，可复现画像脚本；只输出结构特征与计数，不输出正文）
- `docs/reports/P00-sample-log.csv`（16 行抽样明细）
- `docs/reports/P00-data-profile.md`（画像报告，含十问回答与通过标准对照）
- 本文件

### 执行的命令及结果

- `python scripts/profile_sample.py`（RAG 环境）→ 16 份全部出画像，写入 sample-log.csv

### 关键发现

1. **WPS 兼容性坑（影响 9+ 份文件）**：DOCX/XLSX 的 zip 条目为反斜杠路径，python-docx/openpyxl 直接失败；修复 = 临时副本重写条目名（不改原始文件），修法取自 Memory 项目 `RAG/Memory/src/memory/evolution/doc/extract.py`；
2. 验收测试记录表 PDF 为纯扫描（8/8 页无文本层）→ 需 OCR/MinerU（按用户指示本阶段未用）；
3. `.doc` 用 libreoffice 提取（antiword 丢中文）；
4. 无需新增任何依赖。

### 与任务包的偏差

- 抽样 16 份（PDF5/DOCX5/DOC2/XLSX4），超出 ≥12 最低要求以覆盖"履历书"类型；
- PDF 按用户指示使用简单解析器（PyMuPDF/pdfplumber），未用 MinerU。

### 需要决策的问题

1. P01 解析管线是否直接复用 Memory 项目的 WPS 修复与 chunker（parent/child + H1/H2/H3 透传）模式；
2. 纯扫描 PDF（验收测试记录表类）在 P01 的处理顺序（先跳过标记 PENDING，还是提前启用 MinerU）；
3. ~~5 组同名文件登记口径~~ → **已决策（2026-09-01）**：按"主副本 + 副本关联"登记（83 条不动，副本不进检索索引）；判同用 P01 新增 `content_sha256`（提取文本归一化哈希），`checksum_sha256`（全文件字节）保留作完整性锚点；纯扫描件无文本层，走"同尺寸 + 图像相似"兜底。

### 补充决策记录（2026-09-01，用户细化）

**追溯图边类型（P05 图 schema 输入）**——用户在画像报告基础上确认四类文档关系边，均已有数据支撑：

| 边类型 | 数据支撑 | 图上形态 |
|--------|----------|----------|
| 相同文档放不同位置（副本） | 5 组同名文件（工作目录 vs 验收外发国星文件目录） | `Document --副本_of--> Document`（主副本口径见决策 3） |
| 相同文档不同类型 | docx + 盖章扫描 pdf 成对（说明书 V1.0 两种格式） | `Document --签署版_of--> Document` |
| 相似文档多版本迭代 | 程控时间表 8.28→8.31→9.1→9.2；软件版本控制 sheet（UBOOT/CPU 版本序列）；IDS 修订表 | `Document --修订自--> Document`（版本链） |
| 文档之间的关系 | 引用文件章节（大纲 2 处、总结 3 处）、遥测表 4 组关联 sheet、交付清单↔证明书↔履历书 | `Document --引用--> Document`、`Sheet --关联--> Sheet`、`Document --证明--> 实物(Z0102)` |

前三类为版本/副本边，第四类为引用/组成边；每条边必须挂 source_id 证据。

**metadata filter 字段语义**（8 个候选，当前多为 UNKNOWN，P01 解析时填充）：file_format（格式分流）、doc_type（按文档类型收窄）、document_version/effective_version（多版本取生效版）、subsystem（按单机收窄）、filesystem_mtime 日期段（时间约束类问题）、document_status（过滤过期待办）、security_level（权限边界）、H1/H2/H3（章节定位）。

**"暂不适合自动抽取"清单**（确定性解析不可靠，人工或后阶段处理）：扫描件签名/盖章区、公式、图片中的图表、履历书低 CJK 不规则表格、状态词语义判断（"通过"在结论句 vs "通过 CAN 总线"含义不同——P02 引入模型后此项可移出，前提是回答必须回链证据原文）。

## Codex Review

### Review 结果

（待填）

### 发现的问题

（待填）

### 修复任务

（待填）

### 验收状态

（待填）
