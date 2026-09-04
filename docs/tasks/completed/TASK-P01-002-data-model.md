# TASK-P01-002 统一数据模型与数据契约（截断补全版）

## 状态

ACCEPTED（2026-09-04 用户确认，commit 72c828c）

## 所属阶段

P01：数据解析与规范化

## 背景

（见任务包原文，P00 / P01-001 已确认的事实清单。）

## 为什么做

（见任务包原文。本任务目标是稳定、最小、可扩展的数据契约，不是万能文档对象。）

## 目标 / 前置条件 / 输入 / 输出 / 实现约束

（见任务包原文。前置条件已核：TASK-P01-001 已 ACCEPTED 并归档，commit 850fa09。）

# 一、模型之间的关系

统一数据流：

```text
SourceDocument
    ↓
ParseRun
    ↓
DocumentElement
    ↓
ChunkRecord
    ↓
后续索引、RAG、GraphRAG、Wiki
```

- `SourceDocument`：manifest 一行对应的运行时对象，解析与删除传播的主体；
- `ParseRun`：一次解析执行（source × 解析器版本 × 路由），状态机载体，质量报告数据源；
- `DocumentElement`：最小可溯源内容单元（段落/标题/表格行/键值/图占位），携带 `Location`（在哪）与 `Provenance`（谁怎么产出的）；
- `ChunkRecord`：检索粒度单元，只引用 element_ids 不复制溯源字段（溯源经 element 传递）；
- `QualityIssue`：挂在 run/source 上的质量问题记录（只含计数与判定，不含正文）。

## 稳定 ID 规则（补全）

| ID | 规则 | 稳定性 |
|----|------|--------|
| source_id | `SRC-<sha1(relative_path)[:10].upper()>`（P00 既有约定） | 路径不变则不变 |
| element_id | `EL-<sha1(source_id\|element_type\|locator_key\|seq)[:12].upper()>` | 与内容无关：同位置重解析 ID 不变，文本漂移可对比 |
| chunk_id | `CHK-<sha1(element_ids\|strategy)[:12].upper()>` | 输入单元不变则不变 |
| run_id | `RUN-<sha1(source_id\|started_at)[:12].upper()>` | 单次执行唯一 |
| issue_id | `QI-<sha1(run_id\|code\|locator_key)[:12].upper()>` | 同 run 同位置同问题可去重 |

## 验收标准（补全）

1. 七个模型 + 全部枚举在 `src/rag_integration/models.py`，仅标准库；
2. 构造期校验生效：非法 source_id / 空内容 Element / 无锚点 Location / 无表头 TABLE_ROW 均抛异常；
3. `DocumentElement` / `ParseRun` 支持 to_json / from_json 往返无损；
4. `tests/models/` 单测通过（RAG env pytest）；
5. 数据契约文档 `docs/design/P01-data-contract.md` + `docs/design/P01-schema.md` 落档；
6. 不新增依赖、不动 ROADMAP / P01-001 路由 / P00 验收状态。

## 非目标（补全）

- 不实现解析器/路由/OCR/chunking 算法/Embedding/数据库/外部 API；
- 不读取原始航天资料正文进测试（用合成样例）；
- 不定义检索侧索引 schema（P02 职责）。

---

# GLM 实现报告

## 编码前四问

1. **数据流是什么？** manifest → SourceDocument →（路由）ParseRun → DocumentElement（带 Location/Provenance）→（P02）ChunkRecord → 索引。QualityIssue 旁挂 run/source。
2. **哪个模型先被谁消费？** SourceDocument/ParseRun/DocumentElement 由 P01-003~005 的解析管线消费；ChunkRecord 本任务只定形，P02 消费。
3. **违反契约的后果？** 溯源断裂→删除传播失效；空文本入索引→检索命中不了还占库；无表头表格行→命中也无法判读。故这三类在构造期直接抛异常（宁失败不放行）。
4. **现有工具箱缺什么？** 无 pydantic（约束禁止安装）→ stdlib dataclasses + `__post_init__` 校验 + json 默认编码器。

## 截断补全偏离说明

任务包原文在「一、模型之间的关系」数据流图处截断。补全小节：稳定 ID 规则、验收标准、非目标。数据流图与任务包原文一致，未改写。字段/枚举细则见 `P01-schema.md`。

## 产出清单

- `src/rag_integration/__init__.py`、`src/rag_integration/models.py`
- `tests/models/test_models.py`
- `docs/design/P01-data-contract.md`、`docs/design/P01-schema.md`
- 本任务文件

## 自测

`/home/zjlab/anaconda3/envs/RAG/bin/python -m pytest tests/` 全绿（22 旧 + 新增）。
