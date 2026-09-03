# iOS AI Workflow

一套面向 Codex 桌面端的文件化 iOS 团队工作流，不依赖专用 CLI。

## 推荐目录结构

```text
<工作目录>/
├── AGENTS.md
├── MyProject/
├── iOSFlowRecords/
│   ├── index.jsonc            活动需求索引
│   ├── requirements/          单个需求档案
│   └── projects/              各项目的需求执行顺序
└── iOS_Workflow/
    ├── AGENTS.md
    ├── README.md
    ├── CHANGELOG.md
    ├── LICENSE
    ├── config/
    ├── standards/
    ├── templates/
    ├── checklists/
    ├── tools/
    ├── tests/
    └── docs/
```

- `<工作目录>/AGENTS.md`：Codex 自动读取的轻量入口。
- `<工作目录>/MyProject/`：团队成员自己的业务项目和 Git 仓库。
- `<工作目录>/iOSFlowRecords/`：可见的需求台账目录，按项目保存索引、执行顺序、状态和提交记录，由工作流按需创建。
- `<工作目录>/iOS_Workflow/`：独立维护、按 tag 发布的工作流仓库。

`<工作目录>` 只是路径占位符，可以是团队成员已有的任意目录，不要求命名为 `Workspace`。

## 接入方法

1. 选择一个需要在 Codex 中打开的现有工作目录，名称不限。
2. 将工作流放在 `<工作目录>/iOS_Workflow/`，将业务项目放在同级目录，例如 `<工作目录>/MyProject/`。
3. 在该工作目录根部创建 `AGENTS.md`：

   ```md
   # 项目工作流入口

   开始任何编码、提交、推送或 review 工作前，如果当前上下文尚未加载以下文件，则读取并遵循一次：

   - `iOS_Workflow/AGENTS.md`

   工作流中引用的相对路径以 `iOS_Workflow/` 为基准。
   项目自身明确约定和用户当前要求具有更高优先级。
   ```

4. 在 Codex 桌面端打开该工作目录，直接提出项目需求。

入口路径不随工作流版本变化，一个入口可以服务该工作目录下的多个业务项目。团队成员更新 `iOS_Workflow/` 不会修改业务项目的 Git 历史，建议由团队统一指定并切换版本 tag。

注意：文件名必须是 `AGENTS.md`；若工作流目录改名，需要同步修改轻量入口中的路径。原始完整入口始终保留在 `iOS_Workflow/AGENTS.md`。

## 按任务加载，减少 Token

完整入口只负责路由，不再要求每次任务读取所有配置和规范：

- 新功能和缺陷修复先加载精简需求规范；只有需要正式需求卡或补齐信息时才加载对应模板。
- 需求可执行后按风险加载技术设计规范；小改动写精简方案，高风险或跨模块改动才加载完整模板。
- 继续任务时先读取 `iOSFlowRecords/index.jsonc`，再只读取当前需求档案，不扫描全部历史。
- 普通业务修改只加载核心规范和当前使用的 Swift 或 Objective-C 规范。
- 新生成代码额外加载生成与注释规范。
- UI 任务额外加载 UI 规范和 DesignTokens。
- 三方库或编译任务加载依赖规范。
- 新项目才加载默认配置和全部生成所需规则。
- 提交、推送或 review 先加载轻量门禁；订阅和打点模块只在 diff 涉及时加载。
- README、架构说明和历史记录不属于日常任务的必读上下文。
- 已经进入当前上下文的入口或规则文件不会重复读取；组合任务先对文件路径去重。

组合任务加载对应规则的并集。不要为了“可能有用”预读其他文件；命令成功时仅保留摘要，失败时仅保留相关日志。当前 diff、配置和依赖未变化时，可以复用本任务已经成功的安装、构建、测试和静态检查证据。

## 默认配置

新项目默认配置位于 [`config/defaults.jsonc`](config/defaults.jsonc)：Swift、UIKit、MVVM、语言跟随系统、英语本地化、中文注释等级 3、CocoaPods。用户当前明确指定的选项优先。

新生成手写代码的注释规则见 [`code-generation.md`](standards/code-generation.md)。系统方法、继承方法、生命周期和代理/数据源回调不生成解释性注释，也不生成文件元数据或模板化职责标签。

三方库规则见 [`dependencies.md`](standards/dependencies.md)。直接依赖必须使用唯一精确版本；新项目、依赖版本变化和编译前按当前依赖管理方式安装或解析依赖。

## 规则与检查文件

- [`requirements.md`](standards/requirements.md)：编码前的目标、范围、验收标准、影响和完成定义。
- [`requirement-lifecycle.md`](standards/requirement-lifecycle.md)：需求状态、步骤、恢复、Git 关联和完成规则。
- [`technical-design.md`](standards/technical-design.md)：编码前的设计分级、方案内容、ADR 和变更规则。
- [`project-generation.md`](standards/project-generation.md)：配置校验、项目生成顺序、支持组合和验证要求。
- [`feature.md`](templates/requirements/feature.md) 与 [`bug.md`](templates/requirements/bug.md)：按任务类型加载的需求卡模板。
- [`design/feature-design.md`](templates/design/feature-design.md)、[`design/bug-fix-design.md`](templates/design/bug-fix-design.md) 与 [`design/adr.md`](templates/design/adr.md)：完整技术设计和关键决策模板。
- [`tracking/index.jsonc`](templates/tracking/index.jsonc)、[`tracking/requirement.md`](templates/tracking/requirement.md) 与 [`tracking/project-history.jsonc`](templates/tracking/project-history.jsonc)：索引、需求档案和项目执行台账模板。
- [`code-core.md`](standards/code-core.md)：通用命名、架构、日志、隐私和测试基线。
- [`code-swift.md`](standards/code-swift.md)：仅 Swift 项目加载的语言规则。
- [`code-objc.md`](standards/code-objc.md)：仅 Objective-C 或混编项目按需加载的语言规则。
- [`code-generation.md`](standards/code-generation.md)：生成代码和中文注释等级。
- [`dependencies.md`](standards/dependencies.md)：依赖管理、精确版本、安装、更新和编译。
- [`ui-style.md`](standards/ui-style.md) 与 [`design-tokens.jsonc`](config/design-tokens.jsonc)：UI、可访问性、本地化和设计参数。
- [`pre-commit-review.md`](checklists/pre-commit-review.md)：提交、推送和 review 的门禁及模块路由。
- [`core.md`](checklists/core.md)：始终执行的通用检查。
- [`subscription.md`](checklists/subscription.md)：仅订阅相关 diff 执行。
- [`analytics.md`](checklists/analytics.md)：仅打点相关 diff 执行。
- [`requirement-traceability.md`](checklists/requirement-traceability.md)：活动需求与 diff、步骤、验收和 commit 的关联检查。
- [`technical-design.md`](checklists/technical-design.md)：设计等级、完整性、风险和实现一致性检查。
- [`project-generation.md`](checklists/project-generation.md)：新项目与生成器变更的专项检查。
- [`project_generation.py`](tools/project_generation.py)：Codex 内部调用的配置校验、项目骨架、DesignTokens、XcodeGen 和依赖准备模块，不提供面向团队成员的 CLI。
- [`test_project_generation.py`](tests/test_project_generation.py)：覆盖支持组合、失败场景和工程生成的自动化测试。
- [`CHANGELOG.md`](CHANGELOG.md)：工作流规则的集中变更历史。

修改规则时同步更新 `CHANGELOG.md`，通过 review 后再发布新版本。

## 提交与推送门禁

提交代码、推送到远端或 review 会自动触发 Checklist：`✅` 表示通过，`❌` 表示失败，`➖` 表示本次未影响或不适用。任何 `❌` 都会阻止提交或推送并向用户列出处理建议；通过后，提交操作把结果写入提交备注，仅推送操作在结果中报告且不改写已有提交。

提交后立即推送时，如果提交 hash、diff、配置和依赖没有变化，推送阶段复用提交时的 Checklist，只检查远端、上游和工作区状态。Git 成功验证只显示必要摘要，不重复回显完整提交正文或 Checklist。

## 在 Codex 中使用

无需安装插件或运行工作流专用命令，直接输入自然语言，例如：

```text
按照当前工作目录中的 iOS 工作流增加设置页面。
使用 Swift、UIKit 和 MVVM 创建首页与语言设置功能。
提交并推送当前修改。
```

第一条适合已有项目功能开发；第二条用于明确覆盖默认选项；第三条会自动执行提交和推送门禁。

新建项目时 Codex 会先校验默认配置，再调用内部生成器创建源码、DesignTokens、本地化、测试、隐私清单和 XcodeGen 配置；随后生成 Xcode 工程并按配置准备依赖。团队成员仍然只需使用自然语言，不需要直接运行 Python 或工作流命令。若配置非法、目标目录非空、XcodeGen 或依赖工具缺失，流程会停止并说明原因，不会继续编译。

收到新增功能或缺陷任务后，Codex 会先在上下文中整理最小需求卡。只有关键信息会改变方案或验收结果时才询问，不会为了填写模板重复追问；除非用户要求，否则不会在业务仓库创建需求文档。

## 需求执行与恢复

需求需要保存或开始实施时，Codex 在工作目录的 `iOSFlowRecords/` 中创建索引和单文件需求档案。需求首次开始执行时取得不可变的项目顺序号，并写入 `iOSFlowRecords/projects/<项目>/history.jsonc`；完成、阻塞或取消都保留原顺序。步骤使用 `STEP-NNN`，只在状态变化、验证、阻塞、提交和推送时记录摘要，不保存完整命令、日志或 diff。

用户说“继续上次需求”时，Codex 从索引找到活动需求，核对项目、分支、HEAD 和工作区，再从第一个未完成步骤继续。提交正文使用 `Requirement` 和 `Steps` 关联需求；提交成功后记录 hash、完成步骤、验证结果和下一步。只有验收、测试、文档和提交记录全部满足时才标记完成。

用户询问“这个项目执行过哪些需求”时，Codex 只读取对应项目台账，按 `sequence` 输出需求顺序、状态和最终提交，不加载全部需求正文。

## 技术方案与架构设计

需求分析完成后，Codex 在编码前选择设计等级：纯维护可标记 `not_required`；单模块低风险改动使用 `brief` 并写入需求档案；跨模块、公共接口、数据结构、依赖、并发、迁移、隐私安全或订阅支付变化使用 `full` 模板。

设计状态只有 `pending`、`approved`、`not_required`。只有设计通过或明确不需要设计时才能进入实现。影响长期维护的关键选择使用 ADR，普通实现细节不建 ADR；实现偏离已确认设计时，先更新方案和执行步骤。

`iOSFlowRecords/` 是工作目录中可直接查看的运行状态，不属于可更新的 `iOS_Workflow/` 规则目录。是否纳入业务项目版本控制由团队自行决定；工作流源码仓库默认忽略它。
