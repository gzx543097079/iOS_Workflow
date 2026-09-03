# 提交、推送与 Review 门禁

触发提交、推送或 review 时自动执行。

## 状态与范围

- `✅` 通过；`❌` 失败并阻止提交/推送；`➖` 未影响或不适用，须说明原因。
- 提交检查待提交 diff（有暂存区时以其为准）；review 检查完整 diff。
- 推送检查相对上游的提交和工作区。若刚提交且证据键未变，只检查提交 hash、远端、上游和工作区，不重跑或逐项输出 Checklist。

## 条件加载

1. 始终读取 `checklists/core.md`。
2. diff 涉及 StoreKit、商品、价格、购买、收据、订阅或权益时读取 `checklists/subscription.md`，否则整组 `➖`。
3. diff 涉及事件、曝光、点击、分析 SDK、参数、埋点或遥测时读取 `checklists/analytics.md`，否则整组 `➖`。
4. 当前项目存在活动需求或本次提交声明 Requirement ID 时读取 `checklists/requirement-traceability.md`；无关联需求的维护操作整组 `➖` 并说明原因。
5. UI、依赖等规范按 `AGENTS.md` 路由，不加载无关规则。

## 门禁输出

- 适用项逐项标记；整组不适用可合并。任一 `❌` 时输出适用项、失败汇总和建议，然后停止。
- 通过后，提交正文加入 `Checklist`；仅推送时在结果中报告且不改写提交。
- 提交后立即推送且证据键未变，只报告复用的提交 hash 和增量检查结果。
- Checklist 不替代构建、测试或 review。
