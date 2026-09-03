# 提交、推送与 Review 门禁

触发提交、推送或 review 时自动执行。

## 状态与范围

- `✅` 通过；`❌` 失败并阻止提交/推送；`➖` 未影响或不适用，须说明原因。
- 提交检查待提交 diff（有暂存区时以其为准）；review 检查完整 diff。
- 提交检查可复用本任务与当前受测输入匹配的成功证据；仅运行记录、文档或版本元数据变化不重跑测试。推送检查相对上游的提交和工作区，若证据键未变，只检查提交、远端、上游和工作区。

## 条件加载

1. 始终读取 `references/checklists/core.md`。
2. diff 涉及 StoreKit、商品、价格、购买、收据、订阅或权益时读取 `references/checklists/subscription.md`，否则整组 `➖`。
3. diff 涉及事件、曝光、点击、分析 SDK、参数、埋点或遥测时读取 `references/checklists/analytics.md`，否则整组 `➖`。
4. 当前项目存在活动需求或本次提交声明 Requirement ID 时读取 `references/checklists/requirement-traceability.md`；无关联需求的维护操作整组 `➖` 并说明原因。
5. 活动需求需要技术设计，或 diff 涉及架构、公共接口、数据结构、依赖、并发、迁移、隐私安全时读取 `references/checklists/technical-design.md`；否则整组 `➖`。
6. 新建项目，或 diff 涉及 `scripts/project_generation.py`、默认配置和 DesignTokens 生成时读取 `references/checklists/project-generation.md`；否则整组 `➖`。
7. diff 涉及源码、测试、工程配置、依赖、生成器或 Requirement 验收行为时读取 `references/checklists/testing.md`；纯文档且不影响执行行为时整组 `➖`。
8. UI、依赖等规范按 `SKILL.md` 路由，不加载无关规则。

## 门禁输出

- 适用项逐项标记；整组不适用可合并。任一 `❌` 时输出适用项、失败汇总和建议，然后停止。
- 提交标题、提交正文和 Checklist 内容默认使用中文；用户或业务项目明确要求其他语言时除外。
- 通过后，提交正文加入 `Checklist`；仅推送时在结果中报告且不改写提交。
- 提交后立即推送且证据键未变，只报告复用的提交 hash 和增量检查结果。不得为了回写本次提交 hash、推送或 tag 状态再创建记录提交。
- Checklist 不替代构建、测试或 review。
