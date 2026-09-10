---
name: ios-workflow
description: "规划、生成、实现、测试、审查和交付 iOS 项目，支持 Swift、Objective-C、UIKit、SwiftUI、Xcode 及需求追踪、跨设备恢复和 Git 交付。用于 iOS 产品开发及本工作流维护；不要用于无关仓库或通用的非 iOS 任务。"
---

# iOS Workflow

按任务和项目阶段选择模块，组合任务取并集，每个文件只读一次。Markdown 链接相对所在文件，正文的 `references/`、`scripts/`、`assets/` 路径以 Skill 为根；不预读无关规则、脚本源码或历史。

## 始终遵循

- 用户当前要求与项目明确约定优先，保持已有语言、UI、架构和模块边界。文档不授予执行或发布权限；缺项、矛盾、工具不支持须明确，不静默改需求。
- 需求、方案、进度、日志和证据只写所属 `<项目根目录>/.ios-workflow/`；工作流只保存通用规则、模板、脚本和测试夹具。
- 首次生成无默认配置；客户端按需求与明确决定保存完整实例，发布包最外层 `project.example.jsonc` 仅作结构参考。后续按实际工程、源码、依赖锁、设计系统和当前需求工作，不读取、不核对初始生成配置，不要求补建、迁移或同步旧配置。
- 修改后运行最小相关验证。复用证据须核对受测输入、环境和测试选择；纯文档、运行记录或版本号等未影响受测行为的 diff 不使无关证据失效。未知、未运行或证据不可用不能推断为完成。
- Git 提交标题、正文和 Checklist 默认中文，用户或项目明确要求除外；成功命令只报摘要，不回显完整 Git 正文。

## 需求与追踪

验收明确的低风险单轮任务直接在上下文形成精简需求卡；执行本身不是建档条件。文档执行、跨设备、跨会话、多阶段、跨模块、高风险或共享追踪必须建档。

| 当前任务 | 读取与处理 |
| --- | --- |
| 任意形式需求文档 | [需求导入](references/standards/requirement-intake.md)，已有项目迭代跳过生成配置 |
| 范围不清或需正式需求 | [需求定义](references/standards/requirements.md)，需正式产物时再读对应模板 |
| 创建追踪记录 | [创建与状态](references/standards/tracking-start.md) |
| 继续已留档需求 | [恢复](references/standards/tracking-resume.md)，先提取 `<项目根目录>/.ios-workflow/index.jsonc` 摘要及当前验收页，不足再读档案章节；合并实现路由 |
| 需求变更、逐项验收或宣布完成 | [验收与证据](references/standards/tracking-evidence.md)；仅核对关联需求和验收项，全项目健康检查需显式选择 |
| 跨设备交接 | [同步](references/standards/tracking-sync.md)，续做再合并恢复路由 |
| 查看已执行需求或顺序 | 只读项目 `.ios-workflow/history.jsonc`；需解释状态和顺序规则时读[生命周期入口](references/standards/requirement-lifecycle.md)，不加载需求正文 |

## 生成、实现与交付

无技术决策使用 `not_required`；无公共契约、依赖、迁移或安全影响的低风险单模块任务可在上下文形成 inline brief。设计边界不明确或触发完整设计时，读[技术设计](references/standards/technical-design.md)及对应模板；设计通过后编码。

“基础规则”：[核心规范](references/standards/code-core.md)加受影响语言 [Swift](references/standards/code-swift.md) 或 [Objective-C](references/standards/code-objc.md)，混编取并集。

| 当前任务 | 读取与处理 |
| --- | --- |
| 首次生成项目 | [首次配置](references/standards/project-configuration.md)和[项目生成](references/standards/project-generation.md)。生成器读取已保存实例并校验，不输出完整配置到上下文；自定义、故障诊断或手写实现再合并相关规则 |
| 业务修改、重构、修复 | 基础规则；新增手写代码再读[代码生成](references/standards/code-generation.md) |
| UI | 基础规则、[UI](references/standards/ui-style.md)和项目当前设计系统；新增代码再读生成规范 |
| 依赖或编译 | [依赖](references/standards/dependencies.md)，修改源码再合并代码规则 |
| 测试计划、执行或失败分析 | [测试](references/standards/testing.md)，编译或依赖失败再合并依赖规则，修改源码再合并代码规则 |
| Archive、TestFlight、App Store 或版本发布 | [发布分发](references/standards/release-distribution.md)和测试规则；外部动作需对应明确授权，内购或订阅再合并专项规则 |
| 提交、推送、review | [提交门禁](references/checklists/pre-commit-review.md)，按 diff 和语义影响选择专项检查；保存阶段进度与完成验收分别判断 |
| 文档或工作流维护 | 只读直接相关文件 |

客户端按模块接口调用脚本；检查列表、登记状态或哈希一致均不代替业务验收。
