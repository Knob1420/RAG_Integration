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
2. 纯扫描 PDF（验收测试记录表类）在 P01 的处理顺序（先跳过标记 PENDING，还是提前启用 MinerU）。

## Codex Review

### Review 结果

（待填）

### 发现的问题

（待填）

### 修复任务

（待填）

### 验收状态

（待填）
