# TASK-P00-002 生成航天资料元数据清单

## 状态

IMPLEMENTED

## 当前项目事实

- 项目对象：卫星计算载荷—智加 X100 计算模块
- 资料数量：约 83 份
- 文件格式：PDF、DOC、XLSX
- 当前没有代码资料
- 文档命名规则不统一
- 文档版本信息不完整，文件修改时间是目前可观察的版本线索
- 部分文档内部存在引用文件
- 当前阶段：P00 项目范围与资料治理

## 目标

实现一个本地元数据盘点脚本，生成 data_manifest.csv。

## 必须做到

- 递归扫描指定资料目录；
- 识别 PDF、DOC、DOCX、XLSX；
- 记录文件名、相对路径、扩展名、大小、SHA-256、修改时间；
- 为资料生成稳定 source_id；
- 保留已有 source_id；
- 检测文件新增、删除和内容变化；
- 未人工确认的字段填 UNKNOWN；
- 默认不解析正文；
- 默认不输出正文日志；
- 不调用外部模型 API；
- 不把原始资料复制到代码仓库。

## 不要做

- 不实现 PDF/DOC/XLSX 正文解析；
- 不生成 embedding；
- 不建立向量库；
- 不读取文件内容用于 LLM 分析；
- 不把 filesystem_mtime 命名为 document_version；
- 不修改项目路线和阶段状态。

## 验收标准

- 83 份资料能够生成 83 条清单记录；
- source_id 无重复；
- 同一目录重复运行，已有 source_id 不变化；
- 文件内容变化能够通过 checksum 检测；
- 文件新增和删除能够被报告；
- 日志不包含原始正文；
- 测试覆盖空目录、重复运行、新增文件、修改文件和不支持扩展名；
- `pytest` 通过。

## GLM Implementation Report

### 修改文件

- `scripts/build_manifest.py`（新增，清单生成脚本）
- `scripts/__init__.py`（新增，空文件，使 tests 可导入）
- `tests/test_build_manifest.py`（新增，7 个测试）
- `docs/tasks/active/TASK-P00-002-data-manifest.md`（本文件）

### 实现说明

- 单文件脚本，仅用标准库（argparse/csv/hashlib/datetime/pathlib）。
- `source_id = SRC-<sha1(相对路径)前10位大写>`：由相对路径确定性生成，重复运行不变；重扫时同路径沿用旧清单中的 id（内容变化也不换 id，保留资料血缘；引用旧 id 的派生数据不失链）。
- 变更检测：新旧清单按 relative_path 对比，sha256 不同记为"变化"。
- 未知字段：`document_version`、`safety_level` 填 `UNKNOWN`；mtime 字段名 `filesystem_mtime`，未冒充 document_version。
- 输出仅含元数据与哈希，无正文；不解析内容（SHA-256 计算读字节流但不解析、不记录）。
- 相对路径记录，原始资料绝对路径不入仓库。

### 执行的命令及结果

- `/home/zjlab/anaconda3/envs/RAG/bin/python -m pytest tests/ -q` → **8 passed**（空目录/重复运行 id 稳定/新增/删除/修改且 id 不变/不支持扩展名/Office 锁文件排除/UNKNOWN 字段与字段名）
- 解压：`data/x100研制.rar`（330 MB）→ `data/x100研制 - 副本/`，解出 86 个文件
- 真实盘点：`python scripts/build_manifest.py "data/x100研制 - 副本" --output data_manifest.csv` → 见下

### 清单条数

- **83**（验收标准达成：83 份资料 83 条记录）
- 86 个解压文件 = 83 份有效资料 + 2 个 `~$` Office 锁临时文件（脚本排除）+ 1 个 zip（不在支持格式内，未入清单，路径：`3d打印 归档/` 下，待决策是否展开）

### 新增、删除、变化文件数量

- 首次运行：新增 83、删除 0、变化 0
- 立即重复运行：新增 0、删除 0、变化 0（source_id 稳定，`sort | uniq -d` 重复数 0）

### 未实现内容

- 正文解析、embedding、向量库（按任务包属"不要做"）。

### 已知限制

1. source_id 锚定相对路径：文件改名或移动会被报告为"删除+新增"，id 变化（不追踪移动）；
2. 同路径内容变化保留旧 id，此时 source_id 不再唯一对应一份静态内容（以 sha256 区分版本）；
3. `.doc`（旧二进制格式）与 `.docx` 同等对待，仅记录元数据；
4. 资料中存在明显重复内容的不同格式副本（如 `*.docx.pdf` 盖章扫描版与同名 docx），本任务只登记不去重，去重留给 P01；
5. filesystem_mtime 为解压时间，不是原始修改时间（rar 未保留各文件原 mtime）——版本线索弱化，需在 P01 人工确认 document_version。

### 与任务包的偏差

1. 新增 `~$` 锁文件排除规则（任务包未要求，但不排除则 85 条 ≠ 83 条，无法满足验收标准）；
2. 解压用 unrar-cffi（装在 RAG 环境，非项目依赖）——本机无 unrar/7z/p7zip，pip 默认源（清华镜像 403）不可用，改用官方 PyPI 安装；
3. 原始资料位于仓库内 `data/`（用户提供），已通过 `.gitignore` 排除提交——与 DATA_GOVERNANCE"建议仓库外"不完全一致，属用户决策。

### 需要决策的问题

（2026-09-01 用户已决策，均已落实）

1. ~~归档内的 1 个 zip 是否展开~~ → **暂不展开**，保持 83 条口径；
2. `safety_level` 83 条仍为 UNKNOWN，待用户定级（P00 后续任务，只有用户有权定级）；
3. ~~仓库内 `data/` 存放原始资料~~ → **已外迁至仓库外 `../Data`**（rar 与解压文件均在），仓库内 `data/` 已删除；重新盘点 source_id 全部不变（相对路径未变）。

### 补充修正（2026-09-01）

- **filesystem_mtime 修复（根因）**：首次解压未恢复 rar 内保存的原始修改时间，导致 83 条 mtime 全为解压当天、无版本意义。已从 rar 的 `date_time` 恢复并重解压至 `../Data`，现 mtime 范围 2024-03-07 ~ 2025-09-02，当日时间 0 条。sha256 与 source_id 不受影响（新增/删除/变化均 0）。
- 外迁后扫描根目录：`../Data/x100研制 - 副本`（相对路径与原一致，id 稳定）。
- `docs/PROJECT_CONTEXT.yaml` 为用户提供的项目概要（external_model_api: allowed 等），供后续任务参考。

## Codex Review

### Review 结果

（待填）

### 发现的问题

（待填）

### 修复任务

（待填）

### 验收状态

（待填）
