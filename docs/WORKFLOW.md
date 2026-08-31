# 工作流（WORKFLOW）

> 本文件定义项目的三方协作规则与验收制度。

## 三方分工

### 用户

- 确定资料范围；
- 提供领域上下文（术语解释、资料背景、工程常识）；
- 判断问题是否有工程价值；
- 判断资料是否支持回答（对抽样问答做裁决）；
- 决定敏感信息处理方式；
- 对重要技术决策做最终选择。

### Codex

- 维护路线（ROADMAP、阶段门）；
- 拆分任务（从 TASK_TEMPLATE 生成任务包）；
- 设计数据模型和实验；
- 检查 GLM 的实现（代码 review、diff 审核）；
- 分析测试和指标；
- 进行阶段验收；
- 编写修复任务；
- 维护 ADR（docs/decisions）和阶段报告（docs/reports）。

### GLM

- 按任务包编码；
- 编写测试；
- 运行验证命令；
- 汇报修改、测试、限制和偏差（填写任务包的 GLM Implementation Report）；
- 不自行改变项目范围；
- 不自行把任务标记为验收通过。

## 铁律

1. **仓库文件是唯一事实来源。** 项目状态以 docs/（尤其是 CURRENT_STATUS.md、任务包、ADR、报告）为准。
2. **聊天记录不作为项目状态。** 任何在聊天中达成的决定必须落到文档才算数。
3. **编码完成不等于验收通过。** 只有 Codex 依据实际 diff、测试和实验结果验收后才算通过。
4. **Codex 依据实际 diff、测试和实验结果验收**，不依据 GLM 的自述报告；报告与 diff 不符时按未通过处理并登记问题。
5. **每个任务必须有明确输入、输出、非目标和验收标准**（由 TASK_TEMPLATE 保证），缺一不得开工。
6. **GLM 发现范围外问题时必须记录并请求决策**：写入任务包「需要决策的问题」小节，不得顺手修、顺手扩。

## 任务生命周期

```
TASK_TEMPLATE.md 复制
  → docs/tasks/active/TASK-XX-xxx.md（DRAFT，Codex 填背景/目标/验收标准）
  → 用户确认（涉及资料范围或安全时）
  → GLM 实现 + 填写 Implementation Report（状态: IMPLEMENTED）
  → Codex Review（核对 diff、跑测试、查指标）
  → 通过: 填写 Codex Review、验收状态 ACCEPTED，移入 docs/tasks/completed/
  → 不通过: 登记问题与修复任务，任务留在 active 或派生新任务
```

## 阶段生命周期

```
阶段开始: CURRENT_STATUS.md 更新阶段与阻塞项
  → 各任务完成并验收
  → Codex 出阶段报告（docs/reports/PXX-report.md）
  → 对照 docs/phases/ 中该阶段通过标准逐项核验
  → 通过: CURRENT_STATUS.md 推进到下一阶段
  → 不通过: 阻塞项 + 修复任务写回 CURRENT_STATUS.md，禁止推进
```

## 变更规则

- 技术选型、数据模型、路线细节变更 → ADR（docs/decisions/ADR-XXX-title.md）；
- 阶段顺序、验收制度变更 → ADR + 用户书面确认；
- 文档间冲突 → 以 PROJECT_CHARTER > DATA_GOVERNANCE > ROADMAP > 阶段文件 > 任务包 为序解决，并修复低位文档。
