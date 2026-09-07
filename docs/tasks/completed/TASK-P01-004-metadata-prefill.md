# TASK-P01-004 manifest 业务元数据预填

## 状态

ACCEPTED（2026-09-07 用户确认，UNKNOWN 残留选项 A 接受）

## 规则（全部来自路径/文件名确定性信号，不猜）

| 字段 | 规则 | 结果 |
|---|---|---|
| document_type | 文件名关键词 21 条（纪要/IDS/试验大纲/说明书/清单…，具体词在前） | 预填 73 / UNKNOWN 10 |
| subsystem | 关键词（电源/结构/软件/计算模块/载荷） | 预填 67 / UNKNOWN 16 |
| doc_family | 复用 003 find_families（J≥0.5），族名=成员共同基名 | 3 族 9 份 |
| effective_version | 文件名日期（20250120）或程控式短日期（8.31，剥扩展名后取结尾） | 预填 41 |
| document_version | 文件名 V 号 | 预填 4（V1.0 类） |

title/document_internal_id/document_status 仍严格 UNKNOWN（不得伪造），不在本任务预填范围。

## 产出

- `scripts/prefill_metadata.py`；manifest 20 字段（+doc_family）
- `docs/reports/P01-metadata-prefill.md`（逐份 83 行清单）
- validator：PREFILLED_FIELDS 语义（预填字段允许值，产出经报告审计；title/internal_id/status 仍严格）；build_manifest 同步新列+重扫保留
- 测试 57 passed（document_version 严格性断言改为 title——语义变化是本任务设计的一部分）

## 版本族落库效果

| 族 | 成员版本 |
|---|---|
| 程控时间表 | 8.28 / 8.31 / 9.1 / 9.2 |
| d打印星软件配置项测试记录 | 无日期 / 20250114 / 20250609 |
| 智加x初样方案讨论会议纪要 | 20240306 / 20240307 |

检索侧（P02）据此可做：同族默认最新、按版本过滤、对比并排。

## 人工审清单（验收的一部分）

- document_type UNKNOWN 10 份：过程性文档（问题记录/电测表/需求规格/老炼测试/返修报告/签字单/咨询记录等），建议人工定或接受 UNKNOWN；
- subsystem UNKNOWN 16 份：星总体/跨子系统文档。

## 实施备注

- 程控短日期首跑未抓到（`.xlsx` 的点挡住正则），剥扩展名后修正；
- 族名含小写拉丁（d 打印星…）为 stem 归一化的副作用，不影响机器匹配，未做美化。
