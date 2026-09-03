---
name: ios-workflow
description: "Plan, implement, test, generate, review, and deliver iOS projects using the repository's Swift, Objective-C, UIKit, SwiftUI, Xcode, requirement-tracking, and Git workflow. Use for iOS product work; do not use for unrelated repositories or generic non-iOS tasks."
---

# iOS Workflow

相对路径以本 Skill 目录为基准。先判断任务类型，合并并去重对应规则；每个文件每个任务最多读取一次。用户当前要求和业务项目自身的明确约定优先。

## 通用要求

1. 需求、设计和实现保持项目已有语言、UI、架构和模块边界。
2. 修改后运行最小相关验证。证据键只包含受验证影响的源码、配置、依赖锁、环境和测试选择；纯文档、运行记录或版本号等不影响受测行为的 diff 不使证据失效。
3. Git 验证不回显完整提交、tag 或 Checklist 正文。

## 路由

- 新需求：目标、范围和验收明确的低风险单轮任务直接在上下文形成精简需求卡，不加载需求规范。范围不清，或任务需要留档、跨会话、跨模块、多阶段、高风险或共享追踪时，读取 `references/standards/requirements.md`；需要正式需求卡时再读取对应模板，需要持久化时再读取 `references/standards/requirement-lifecycle.md`。执行本身不是建档条件。
- 技术方案：无技术决策的维护任务标记 `not_required`；单模块且无公共契约、依赖、迁移或安全影响的低风险任务可在上下文形成 inline brief。设计边界不明确或触发完整设计时，读取 `references/standards/technical-design.md`，并仅加载对应 Feature、Bug Fix 或 ADR 模板；设计通过后再编码。
- 继续、变更、阻塞或完成已留档需求：读取 `references/standards/requirement-lifecycle.md`，先读 `<工作目录>/iOSFlowRecords/index.jsonc` 的活动摘要；摘要不足时才按章节读取当前需求档案。
- 查看项目执行过的需求或执行顺序：读取生命周期规范和 `iOSFlowRecords/projects/<项目>/history.jsonc`，不加载全部需求正文。
- 执行已留档需求：确认需求档案和当前步骤后合并实现路由；仅在阶段边界、范围变化、阻塞、关键验证和 Git 交付时更新记录。
- 新项目：先只读取 `references/standards/project-generation.md` 并调用 `scripts/project_generation.py`。配置和 DesignTokens 由生成器直接读取 `assets/config/` 并校验，不输出到模型上下文。只有用户自定义生成结果、生成器失败需诊断或骨架生成后继续手工实现时，才按实际影响加载其他规则。
- 新增手写代码：读取核心规范、所用语言规范和 `references/standards/code-generation.md`。
- 业务修改、重构或修复：读取核心规范和所用语言规范；新增代码再加载生成规范。
- UI：读取核心规范、所用语言规范、`references/standards/ui-style.md` 和 `assets/config/design-tokens.jsonc`；新增代码再加载生成规范。
- 依赖或编译：读取 `references/standards/dependencies.md`；修改源码时再加载对应代码规范。
- 测试计划、执行测试或分析失败：读取 `references/standards/testing.md`；依赖或编译失败再合并依赖规范，修改源码时再合并对应代码规范。
- 提交、推送或 review：读取 `references/checklists/pre-commit-review.md`，并按其条件加载检查模块、技术设计、项目生成、测试和需求追溯检查。
- 文档或工作流维护：只读取直接相关文件。

核心规范为 `references/standards/code-core.md`；语言规范按实际代码选择 `references/standards/code-swift.md`、`references/standards/code-objc.md` 或两者。仓库 README、架构文档和历史记录不是日常必读上下文。
