# P00 Manifest 验证报告（TASK-P00-003A）

日期：2026-09-01 · 验证对象：`data_manifest.csv` · 验证脚本：`scripts/validate_manifest.py`

## 1. Manifest 实际路径

- 仓库根 `data_manifest.csv`，仅此一份；不存在 `data manifest.csv` 或其他副本，无需统一命名。

## 2. 实际记录数量

- **83**（47 docx + 26 pdf + 8 xlsx + 2 doc），与登记资料数一致，无需解释差异。

## 3. 字段清单（18 列）

`source_id, file_name, relative_path, file_extension, file_size, checksum_sha256, filesystem_mtime, document_type, title, document_internal_id, document_version, effective_version, document_status, subsystem, security_level, external_model_allowed, parse_status, notes`

## 4. 缺失字段统计

- **0**。任务包要求的 18 个字段全部存在。
- ~~9 个待人工确认字段全部 `UNKNOWN`~~ → **2026-09-01 用户定级**：`security_level` 83 条全部 **内部可用**，`external_model_allowed` 83 条全部 **YES**（仅使用公司提供的模型 API）。其余 7 个字段（document_type / title / document_internal_id / document_version / effective_version / document_status / subsystem）仍显式 `UNKNOWN`，无伪造值。
- `parse_status` 全部 `NOT_STARTED`（统一枚举；真实状态，非猜测）。
- 重扫保留：已确认值（非 UNKNOWN）在重新扫描时自动沿用，不会被冲回 UNKNOWN（有测试）。

## 5. 重复 source_id

- **0**；非空率 100%。

## 6. 重复 checksum

- **0**（83 个内容哈希全不同）。
- 但有 **5 个重复 file_name**（同名文件出现在不同目录，内容不同）：P01 需做同名消歧与 `*.docx.pdf` 盖章版/原始版关联，本轮只登记。

## 7. 新增、删除、变化文件数量

- 本次重建（新 18 列 schema）：83/0/0（旧文件删除重建）；
- 随后重复扫描：**0/0/0**，source_id 稳定（锚定资料集合内相对路径）。

## 8. 敏感信息检查

- 无本机绝对路径（relative_path 相对资料根）；
- 无原始正文（清单仅元数据+哈希）；
- 无 API Key / token / 密码 / 模型响应（正则扫描通过）；
- filesystem_mtime 与 document_version 为两个独立字段，格式统一 ISO（2024-03-07 ~ 2025-09-02）。

## 9. 执行的命令及结果

| 命令 | 结果 |
|------|------|
| `pytest tests/ -q`（RAG 环境） | **17 passed**（build 8 + validate 9） |
| `python scripts/build_manifest.py ../Data/x100研制\ -\ 副本 --output data_manifest.csv` | 83 条，重扫 0/0/0 |
| `python scripts/validate_manifest.py data_manifest.csv` | **验证通过: 无问题**（退出码 0） |

验收标准中"空目录/重复运行/新增/修改/删除/不支持扩展名"测试由 `tests/test_build_manifest.py`（P00-002）覆盖；`tests/test_manifest_validation.py` 覆盖验证器自身的 9 个失败/成功路径。

## 10. 修改文件

- `scripts/build_manifest.py`：字段对齐任务包契约（`extension→file_extension`、`size_bytes→file_size`、`sha256→checksum_sha256`、`safety_level→security_level`），新增 9 个 UNKNOWN 列 + `parse_status/notes`
- `scripts/validate_manifest.py`：新增（只读 CSV，stdlib only）
- `tests/test_manifest_validation.py`：新增（9 用例）
- `tests/test_build_manifest.py`：字段改名适配 + UNKNOWN 字段断言扩展
- `data_manifest.csv`：按新 schema 重建
- 本报告

## 11. 已知限制

1. 验证器不触文件系统，"文件与磁盘一致"依赖 build 脚本的 sha256 变更检测（已有测试）；
2. `external_model_allowed` 与 `security_level` 目前 UNKNOWN——PROJECT_CONTEXT 的全局 `allowed` 不能替代逐份定级；
3. 5 组同名文件与多组"docx + 盖章 pdf 版"内容关联留给 P01；
4. 验证器只认任务包定义的字段契约，P01 若改 schema 需同步 `REQUIRED_FIELDS/UNKNOWN_OK_FIELDS`。

## 12. 与任务包的偏差

1. 存量清单字段名与任务包契约不一致——**重命名旧字段**而非新建清单（P01 前无下游依赖，git 有旧版可回溯）；
2. 任务包列出的 `subsystem` 在"必须检查"清单未出现但在"可 UNKNOWN"清单出现，已按需存在并填 UNKNOWN。

## 13. 需要用户确认的问题

1. ~~`security_level` / `external_model_allowed` 定级~~ → **已确认（2026-09-01）**：全部"内部可用"/"YES"，仅使用公司模型 API；
2. 5 组同名文件是否视为不同版本/不同文件，还是需要 P01 合并登记口径；
3. 字段重命名（extension 等 4 项）是否需要补一条 ADR 记录 schema 变更。
