# TASK-P00-003A 验收航天资料 Manifest

## 状态

IMPLEMENTED

## 目标

检查现有 data_manifest.csv 是否满足项目数据治理和后续解析要求，并生成一份验证报告。

## 验收标准

（见任务包原文；全部满足——完整验证结果与统计见 `docs/reports/P00-manifest-validation.md`）

## GLM Implementation Report

### 修改文件

- `scripts/build_manifest.py`（字段契约对齐：4 项改名 + 9 个 UNKNOWN 列 + parse_status/notes）
- `scripts/validate_manifest.py`（新增验证器，只读 CSV，stdlib only）
- `tests/test_manifest_validation.py`（新增，9 用例）
- `tests/test_build_manifest.py`（字段改名适配 + UNKNOWN 断言扩展）
- `data_manifest.csv`（新 schema 重建，83 条）
- `docs/reports/P00-manifest-validation.md`（完整验证报告）

### 执行的命令及结果

- `pytest tests/ -q` → **17 passed**
- `build_manifest.py`（新 schema）→ 83 条；重扫 0/0/0（id 稳定）
- `validate_manifest.py data_manifest.csv` → **验证通过: 无问题**（83 条、18 字段、source_id 非空/唯一 100%、无绝对路径/正文/凭证、mtime 格式统一、parse_status 枚举合法）

### 关键数字

- 记录 83（47 docx / 26 pdf / 8 xlsx / 2 doc）；重复 source_id 0；重复 checksum 0；重复 file_name 5（同名不同内容，P01 消歧）
- 全 UNKNOWN 字段 9 个，均显式标记，无伪造值

### 与任务包的偏差

1. 存量字段名（extension/size_bytes/sha256/safety_level）与任务契约不一致 → 改名而非另建清单；
2. 中途重扫一度因旧字段名残留崩溃，已修复（变更检测引用 checksum_sha256），旧 CSV 删除重建。

### 需要决策的问题

1. ~~security_level / external_model_allowed 定级~~ → **已确认（2026-09-01）**：83 条全部 `内部可用` / `YES`（仅公司模型 API）；清单已填入，重扫保留已确认值（新增测试覆盖），验证器改为枚举校验（19 tests passed）；
2. 5 组同名文件 P01 的登记口径；
3. 字段 schema 变更是否补 ADR。

## Codex Review

### Review 结果

（待填）

### 发现的问题

（待填）

### 修复任务

（待填）

### 验收状态

（待填）
