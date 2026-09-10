# 提交、推送与 Review 门禁

触发提交、推送或 review 时自动执行。

## 状态与范围

- 门禁 `✅` 表示本次操作检查通过；门禁 `❌` 阻止提交/推送；`➖` 为未影响或不适用，须说明原因。构建、测试和验收结果单独保留 `passed`、`failed`、`unknown` 等真实状态，不能由保存门禁通过改写为成功。
- 提交检查待提交 diff（有暂存区时以其为准）；review 检查完整 diff。
- 提交检查可复用本任务与当前受测输入匹配的成功证据；仅运行记录、文档或版本元数据变化不重跑测试。推送检查相对上游的提交和工作区，若证据键未变，只检查提交、远端、上游和工作区。

## 阶段保存与验收交付

- 用户要求保存阶段进度或跨设备交接时使用 `operation=checkpoint`；阶段提交及其明确授权的推送均沿用该模式。检查修改范围、隐私、用户文件保护、记录真实性与可恢复性；这些检查失败或未知仍阻止保存。未完成、未验证或已知失败如实保留，不要求先完成整个需求。
- 普通提交核对本次 diff 的相关验证；宣布需求完成或发布时才要求对应范围全部验收通过。所有模式仍须处理覆盖用户文件、暴露凭据、丢失记录等实际问题，不能用“阶段保存”掩盖。
- 状态含义不变：失败结果保留为失败，阶段提交成功仅说明内容已保存，不表示功能验收通过。

可调用 `scripts/change_scope.py` 的 `select_checks(changed_paths, operation=..., impacts=..., requirement_ids=...)` 返回适用清单和追溯范围。路径只提供线索，调用方必须补充依赖、隐私、订阅等语义影响；结果不是通过结论。

实际检查后可调用同模块 `assess_gate(changed_paths, integrity=..., operation=..., impacts=..., requirement_ids=..., validation_result=..., completion_result=...)`。`integrity` 显式提供 `scope`、`privacy`、`user_files`、`records` 的 `passed`/`failed`/`unknown`，来自当前事实而非接口猜测。返回 `gate_passed` 与原验证状态；checkpoint 允许如实保存验证失败或未知，但不得同时宣称相应验收通过。普通提交、推送或 review 仍要求本次相关验证通过，发布还要求对应完成证据；接口不执行 Git、不检查事实、不授予权限。

## 条件加载

0. 后续版本按实际 diff、当前工程与需求检查，不读取或核对初始生成配置；历史生成配置不构成提交或推送门禁。
1. 始终读取 `references/checklists/core.md`。
2. diff 涉及 StoreKit、商品、价格、购买、收据、订阅或权益时读取 `references/checklists/subscription.md`，否则整组 `➖`。
3. diff 涉及事件、曝光、点击、分析 SDK、参数、埋点或遥测时读取 `references/checklists/analytics.md`，否则整组 `➖`。
4. 本次修改关联活动需求、声明 Requirement ID 或改变对应验收行为时读取 `references/checklists/requirement-traceability.md`；无关联需求的维护操作整组 `➖` 并说明原因；账本存在本身不触发全项目核验。
5. 活动需求需要技术设计，或 diff 涉及架构、公共接口、数据结构、依赖、并发、迁移、隐私安全时读取 `references/checklists/technical-design.md`；否则整组 `➖`。
6. 首次生成项目，或维护 `scripts/project_generation.py`、分发配置示例和 DesignTokens 生成逻辑时读取 `references/checklists/project-generation.md`；否则整组 `➖`。
7. diff 涉及源码、测试、工程配置、依赖、生成器或 Requirement 验收行为时读取 `references/checklists/testing.md`；纯文档且不影响执行行为时整组 `➖`。
8. diff 涉及版本号、签名、Capability、Entitlement、ExportOptions、Archive、TestFlight、App Store 元数据或发布自动化时读取 `references/checklists/release-distribution.md`；否则整组 `➖`。
9. UI、依赖等规范按 `SKILL.md` 路由，不加载无关规则。

## 门禁输出

- 适用项按当前操作逐项标记；整组不适用可合并。任一门禁 `❌` 时输出适用项、失败汇总和建议，然后停止。checkpoint 中已如实记录的测试 `failed`/`unknown` 不自动构成保存门禁 `❌`，实际完整性问题仍构成阻断。
- 提交标题、提交正文和 Checklist 内容默认使用中文；用户或业务项目明确要求其他语言时除外。
- 通过后，提交正文加入 `Checklist`；仅推送时在结果中报告且不改写提交。
- 提交后立即推送且证据键未变，只报告复用的提交 hash 和增量检查结果。不得为了回写本次提交 hash、推送或 tag 状态再创建记录提交。
- Checklist 不替代构建、测试或 review。

跨设备交接时核对项目内需求、进度和轻量证据随业务代码同步，确认 Git 忽略规则没有排除必要记录；没有推送授权时只完成本地记录并说明待同步，不声称其他设备已可恢复。
