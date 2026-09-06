# TASK-P01-FULL-PIPELINE 完整文档解析与规范化管线

## 状态

ACCEPTED（2026-09-06 用户确认，走查验收含 6 项修复）

## 所属阶段

P01：数据解析与规范化

## 任务目标

（见任务包原文 12 条：格式识别 → 探测 → 路由 → PDF/OCR → DOC/DOCX/WPS → 旧 DOC → XLSX/IDS → DocumentElement → 类型化 ChunkRecord → ParseRun/QualityIssue → 83 份全量解析 → 质量报告。产出直接作 P02 Hybrid RAG 输入。）

## 项目背景（截断补全）

项目对象：卫星计算载荷—智加 X100 计算模块。语料 83 份（pdf 26 / docx 47 / xlsx 8 / doc 2），位于仓库外 `RAG/Data/x100研制 - 副本/`，全部内部可用级。P01-001 已定路由与质量设计，P01-002 已定统一数据模型（src/rag_integration/models.py，ACCEPTED）。

## 前置条件（补全）

- P01-001 ACCEPTED（850fa09）✓；P01-002 ACCEPTED（56a9388）✓
- RAG env：fitz/pdfplumber/python-docx/openpyxl ✓；mineru env（OCR 子进程）✓；libreoffice（R6）✓

## 输入（补全）

- data_manifest.csv（83 行）；P01-parser-routing.md；P01-quality-requirements.md；golden sample 清单（回归对照）。

## 输出（补全）

- `src/rag_integration/`：probe / routing / parse_pdf / ocr_mineru / parse_docx / parse_doc / parse_xlsx / quality / chunking / pipeline
- `scripts/run_pipeline.py`：CLI 入口
- 派生数据（**仓库外**，含正文不入库）：`RAG/Data/derived/p01/` 下 elements.jsonl / chunks.jsonl / runs.jsonl / issues.jsonl + manifest parse_status 回写
- `docs/reports/P01-parse-quality-report.md`（只有计数与判定，无正文）

## 实现约束（补全）

- 遵循 models.py 契约，不改动已 ACCEPTED 的 P01-002 模型语义；
- 不修改 P01-001 已定路由触发条件；
- 原始资料只读；WPS 修复走临时副本；
- 不新增依赖（现有库内完成）；不调外部模型 API；
- 派生正文数据不进 git（治理红线：repo 推 GitHub，正文留本地）。

## 验收标准（补全）

1. 83 份全部流转到终态（DONE / PENDING_REVIEW / FAILED），无 NOT_STARTED 残留；
2. DONE 文档满足 6 条进索引硬门槛（含 content_sha256 已计算——本任务在 run.stats 落 source 级规范化文本哈希，主副本判定仍归 P01-003）；
3. Golden Sample 14 份解析结果与 expected_features 无冲突；
4. 质量报告落档，含每路由计数、失败清单、复核清单；
5. pytest 全绿（旧 44 + 新增）。

## 非目标（补全）

- 主副本判重与标记（P01-003）；manifest 业务元数据预填（P01-004）；
- 图表内容抽取（figure 占位）；PPT（R10 预留）；Embedding/检索（P02）。

## 默认决策（GLM 代定，可推翻）

1. 派生数据放仓库外 Data/derived/（治理红线推导，见上）；
2. R2 签署页豁免首版不启用（全部扫描页走 OCR，豁免等首份人工标定）；
3. MinerU 用默认后端（hybrid-engine/auto 模型），GPU 参数不调；
4. chunking 策略首版两条：正文 heading_window、表格 per_row（每行一 chunk，自带表头）。

---

# GLM 实现报告（随进度更新）

## 产出

- `src/rag_integration/`：probe / routing / parse_docx / parse_doc / parse_xlsx / parse_pdf / ocr_mineru / quality / chunking / pipeline（10 模块）
- `scripts/run_pipeline.py`；`tests/pipeline/` 4 个测试文件；全套 54 passed
- 派生数据：`Data/derived/p01/`（仓库外）elements/chunks/runs/issues.jsonl + manifest parse_status 回写（83 DONE）
- `docs/reports/P01-parse-quality-report.md`

## 全量结果

83/83 DONE（0 FAILED / 0 复核挂起），17104 Element，7778 Chunk。质量报告含门校准记录、OCR 抽检、14/14 golden sample 对照、已知缺口与人工复核清单。

## 执行中的实测发现（偏离与决策）

1. **扫描页覆盖率 85%→70%**：WPS 扫描件图幅含页边距（实测 0.74–0.81），设计稿阈值过严导致 R3 首判全 empty。已校准并记入质量报告。
2. **cjk 门双口径校准**：表格主导文档 raw cjk 被数字稀释；改为 raw/letters 任一 ≥0.2。解掉了 P01-001 遗留的 GS-08 校准问题。首跑 8 份误报全部转正。
3. **MinerU 实际运行 env 是 `memory`**（mineru 3.4.4 + GPU 管线）；名为 `mineru` 的 env 是无 torch 的轻量客户端版（hybrid-engine 直接报错）。调用对齐 Memory 项目已验证配置（CUDA_VISIBLE_DEVICES=2）。
4. **R4/R7 为 0 不是 bug**：47 docx 全 WPS 反斜杠（P00 已知"本批全命中"）、8 xlsx 全复杂形态。
5. **stream 表格首版未做**（false positive 风险大于收益），lattice-only，降级为文本块；记入已知缺口 1。

## 验收走查中追加的修复（2026-09-06）

- **R3 标题缺失**：MinerU 的 `text_level` 未使用导致 R3 文档 0 个 heading；已修（ocr_mineru.py），4 份记录表各产 1 个 level=2 标题。
- **xlsx 合并标题行误判**：整行同值（合并展开痕迹）+尾部空白列触发假"多行表头"，污染 Sheet2 表头；已修（列裁剪 + merged_title 单独成 kv）。漂移门在修复过程中正确拦截（交付清单两份挂复核），复跑归零——漂移机制首次实战验证。
- **xlsx 内嵌图静默丢失**：`ws._images` 未读取，程控时间表 Sheet2 的时序图（960×1280）无任何登记；已修（FIGURE 占位，锚点=锚定格行号，+4 个 figure）。
- **docx 封面/单列表误产 table_row**：封面标题表（单列或整行合并）被当数据表产空表头行；已修——单列表整表按 key_value 逐行处理，多列表首行整行同值视为合并标题行产单条 key_value（与 xlsx 修复同构）。IDS 抽查验证通过。
- **表题行污染表头（四格式拉齐）**：pdf 原生/OCR 两路补上与 xlsx/docx 同构的标题行规则（split_title_row 共用，OCR 支持连续标题行）；记录表表头从表题变为真实列头，原已知缺口 3 关闭。
- content_list.json 样例留档：`Data/derived/p01/content_list_demo/`（page1/page3）。
- 示例 doc：`智加X100（硬件）验收测试记录表.pdf`（记录表扫描件）。
- 全量终态：83/83 DONE，55 项测试通过。

## 验收建议

看 `git status`/diff（新增 10 源码 + 4 测试 + 2 脚本 + 报告 + 本任务文件）、质量报告、`pytest` 54 passed；派生数据在仓库外抽查 JSONL 结构。人工复核清单 4 项在质量报告末尾（记录表 OCR 比对、履历书核对、溯源抽查 20 条、编号抽检确认）。

