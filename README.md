# iOS AI Workflow

一套面向 Codex 的仓库级 iOS Skill，采用官方 `.agents/skills` 结构，不依赖专用 CLI。

## 推荐目录结构

```text
<工作目录>/
├── AGENTS.md
├── .agents/
│   └── skills/
│       └── ios-workflow/
│           ├── SKILL.md
│           ├── agents/
│           ├── references/
│           │   ├── standards/
│           │   └── checklists/
│           ├── assets/
│           │   ├── config/
│           │   └── templates/
│           └── scripts/
├── MyProject/
├── iOSFlowRecords/
│   ├── index.jsonc            活动需求索引
│   ├── requirements/          单个需求档案
│   ├── projects/              各项目的需求执行顺序
│   └── tests/                 跨会话测试计划与报告
├── tests/                      Skill 与生成器测试
├── docs/
├── README.md
├── CHANGELOG.md
└── LICENSE
```

- `<工作目录>/AGENTS.md`：Codex 自动读取的精简、永久项目规则。
- `<工作目录>/.agents/skills/ios-workflow/`：Codex 自动发现并按需加载的 iOS 工作流 Skill。
- `<工作目录>/MyProject/`：团队成员自己的业务项目和 Git 仓库。
- `<工作目录>/iOSFlowRecords/`：可见的需求台账目录，按项目保存索引、执行顺序、状态和提交记录，由工作流按需创建。

`<工作目录>` 只是路径占位符，可以是团队成员已有的任意目录，不要求命名为 `Workspace`。

## 接入方法

1. 克隆本仓库，或把 `.agents/skills/ios-workflow/` 复制到目标仓库的同一路径。
2. 在 Codex 中打开包含 `.agents/` 的仓库根目录；Codex 会读取 Skill 的 `name` 和 `description` 并按任务自动选择。
3. 目标仓库的 `AGENTS.md` 只保留始终生效的项目规则，也可以明确提示使用 Skill：

   ```md
   # 项目约定

   项目自身明确约定和用户当前要求具有更高优先级。
   iOS 需求、设计、开发、测试、提交或 review 使用 `$ios-workflow`。
   ```

4. 直接提出项目需求，或使用 `$ios-workflow` 显式调用。

Skill 入口固定为 `.agents/skills/ios-workflow/SKILL.md`。该文件包含官方要求的 `name` 和 `description` 元数据；详细规则、模板和脚本只在任务需要时加载。

## 按任务加载，减少 Token

完整入口只负责路由，不再要求每次任务读取所有配置和规范：

- 新功能和缺陷修复先加载精简需求规范；只有需要正式需求卡或补齐信息时才加载对应模板。
- 需求可执行后按风险加载技术设计规范；小改动写精简方案，高风险或跨模块改动才加载完整模板。
- 继续任务时先读取 `iOSFlowRecords/index.jsonc`，再只读取当前需求档案，不扫描全部历史。
- 普通业务修改只加载核心规范和当前使用的 Swift 或 Objective-C 规范。
- 新生成代码额外加载生成与注释规范。
- UI 任务额外加载 UI 规范和 DesignTokens。
- 三方库或编译任务加载依赖规范。
- 测试计划、执行或失败分析加载测试规范；证据键未变化时复用结果，flaky 确认最多额外复跑一次。
- 新项目才加载默认配置和全部生成所需规则。
- 提交、推送或 review 先加载轻量门禁；订阅和打点模块只在 diff 涉及时加载。
- README、架构说明和历史记录不属于日常任务的必读上下文。
- 已经进入当前上下文的入口或规则文件不会重复读取；组合任务先对文件路径去重。

组合任务加载对应规则的并集。不要为了“可能有用”预读其他文件；命令成功时仅保留摘要，失败时仅保留相关日志。当前 diff、配置和依赖未变化时，可以复用本任务已经成功的安装、构建、测试和静态检查证据。

## 默认配置

新项目默认配置位于 [`defaults.jsonc`](.agents/skills/ios-workflow/assets/config/defaults.jsonc)：Swift、UIKit、MVVM、语言跟随系统、英语本地化、中文注释等级 3、CocoaPods。用户当前明确指定的选项优先。

新生成手写代码的注释规则见 [`code-generation.md`](.agents/skills/ios-workflow/references/standards/code-generation.md)。系统方法、继承方法、生命周期和代理/数据源回调不生成解释性注释，也不生成文件元数据或模板化职责标签。

三方库规则见 [`dependencies.md`](.agents/skills/ios-workflow/references/standards/dependencies.md)。直接依赖必须使用唯一精确版本；新项目、依赖版本变化和编译前按当前依赖管理方式安装或解析依赖。

## 规则与检查文件

- [`requirements.md`](.agents/skills/ios-workflow/references/standards/requirements.md)：编码前的目标、范围、验收标准、影响和完成定义。
- [`requirement-lifecycle.md`](.agents/skills/ios-workflow/references/standards/requirement-lifecycle.md)：需求状态、步骤、恢复、Git 关联和完成规则。
- [`technical-design.md`](.agents/skills/ios-workflow/references/standards/technical-design.md)：编码前的设计分级、方案内容、ADR 和变更规则。
- [`project-generation.md`](.agents/skills/ios-workflow/references/standards/project-generation.md)：配置校验、项目生成顺序、支持组合和验证要求。
- [`testing.md`](.agents/skills/ios-workflow/references/standards/testing.md)：测试分层、最小矩阵、证据复用、失败分类和 flaky test 处理。
- [`templates/`](.agents/skills/ios-workflow/assets/templates)：需求、设计、追踪与测试产物模板。
- [`code-core.md`](.agents/skills/ios-workflow/references/standards/code-core.md)：通用命名、架构、日志、隐私和测试基线。
- [`code-swift.md`](.agents/skills/ios-workflow/references/standards/code-swift.md)：仅 Swift 项目加载的语言规则。
- [`code-objc.md`](.agents/skills/ios-workflow/references/standards/code-objc.md)：仅 Objective-C 或混编项目按需加载的语言规则。
- [`code-generation.md`](.agents/skills/ios-workflow/references/standards/code-generation.md)：生成代码和中文注释等级。
- [`dependencies.md`](.agents/skills/ios-workflow/references/standards/dependencies.md)：依赖管理、精确版本、安装、更新和编译。
- [`ui-style.md`](.agents/skills/ios-workflow/references/standards/ui-style.md) 与 [`design-tokens.jsonc`](.agents/skills/ios-workflow/assets/config/design-tokens.jsonc)：UI、可访问性、本地化和设计参数。
- [`checklists/`](.agents/skills/ios-workflow/references/checklists)：提交、推送、review 和条件专项门禁。
- [`project_generation.py`](.agents/skills/ios-workflow/scripts/project_generation.py)：Codex 内部调用的配置校验、项目骨架、DesignTokens、XcodeGen 和依赖准备模块，不提供面向团队成员的 CLI。
- [`test_project_generation.py`](tests/test_project_generation.py)：覆盖支持组合、失败场景和工程生成的自动化测试。
- [`CHANGELOG.md`](CHANGELOG.md)：工作流规则的集中变更历史。

修改规则时同步更新 `CHANGELOG.md`，通过 review 后再发布新版本。

## 示例项目

仓库根目录的 [`WorkflowDemo`](WorkflowDemo/) 是使用本工作流生成并继续开发的真实 UIKit/MVVM 项目，包含计数、设置、12 种语言切换、关于我们、单元测试和 UI 测试，可用于查看工作流交付结果。

## 提交与推送门禁

提交代码、推送到远端或 review 会自动触发 Checklist：`✅` 表示通过，`❌` 表示失败，`➖` 表示本次未影响或不适用。任何 `❌` 都会阻止提交或推送并向用户列出处理建议；通过后，提交操作把结果写入提交备注，仅推送操作在结果中报告且不改写已有提交。

提交后立即推送时，如果受测源码、配置、依赖和测试选择没有变化，推送阶段复用提交时的 Checklist，只检查远端、上游和工作区状态。Git 成功验证只显示必要摘要，不重复回显完整提交正文或 Checklist。

## 在 Codex 中使用

无需安装插件或运行工作流专用命令，直接输入自然语言，例如：

```text
按照当前工作目录中的 iOS 工作流增加设置页面。
使用 Swift、UIKit 和 MVVM 创建首页与语言设置功能。
提交并推送当前修改。
```

第一条适合已有项目功能开发；第二条用于明确覆盖默认选项；第三条会自动执行提交和推送门禁。

新建项目时 Codex 调用内部生成器，由生成器直接读取并校验默认配置和 DesignTokens，再创建源码、本地化、测试、隐私清单和 XcodeGen 配置；完整配置不会先进入模型上下文。团队成员仍然只需使用自然语言，不需要直接运行 Python 或工作流命令。若配置非法、目标目录非空、XcodeGen 或依赖工具缺失，流程会停止并说明原因，不会继续编译。

测试任务会先把 Requirement 验收项映射到单元、集成、UI 或专项验证，再选择最小充分的设备和系统矩阵。低风险结果可记录在需求档案；跨模块、高风险或跨会话任务使用 `iOSFlowRecords/tests/` 中的计划和报告。环境阻塞、真实失败和 flaky test 会分别报告，不会通过无限重试或跳过测试制造通过结果。

收到目标明确的低风险任务后，Codex 直接在上下文中整理精简需求卡和 inline brief；范围不清、需要留档或触发完整设计时才加载对应规范。只有关键信息会改变方案或验收结果时才询问，不会为了填写模板重复追问；除非用户要求，否则不会在业务仓库创建需求文档。

## 需求执行与恢复

只有用户明确要求留档，或任务跨会话、跨模块、多阶段、高风险、需要共享追踪时，Codex 才在工作目录的 `iOSFlowRecords/` 中创建索引和单文件需求档案；低风险、可在单轮完成的改动只在当前上下文保留精简需求卡，开始执行本身不会触发建档。需求首次开始执行时取得不可变的项目顺序号，并写入 `iOSFlowRecords/projects/<项目>/history.jsonc`；完成、阻塞或取消都保留原顺序。步骤使用 `STEP-NNN`，同一阶段内连续步骤合并记录，不保存完整命令、日志或 diff。

活动索引只保存一个完整恢复摘要和最后使用的 Requirement ID，不再随历史增长。用户说“继续上次需求”时，Codex 先读取索引，摘要足够即可继续；只有范围、步骤、设计或历史信息不足时才按章节读取需求档案。需求完成或取消后从活动索引移除，历史仍保留在项目台账和需求档案中。

需求在验收、必要测试和文档同步完成后即可标记 `done`。Git 提交正文中的 `Requirement` 和 `Steps` 是权威关联，提交与推送状态从 Git 日志、上游和远端引用实时判断；不会为了把当前提交 hash 或推送状态写回档案而制造额外提交。

用户询问“这个项目执行过哪些需求”时，Codex 只读取对应项目台账，按 `sequence` 输出需求顺序和状态，不加载全部需求正文；需要提交信息时再从 Git 日志按 Requirement ID 查询。

## 技术方案与架构设计

需求分析完成后，Codex 在编码前选择设计等级：纯维护可标记 `not_required`；单模块低风险改动，以及不改变公共契约的简单新增页面或内部模块使用 `brief`；跨模块、公共接口、数据结构、依赖、并发、迁移、隐私安全或订阅支付变化使用 `full` 模板。“新增模块”本身不自动升级为完整设计。

设计状态只有 `pending`、`approved`、`not_required`。只有设计通过或明确不需要设计时才能进入实现。影响长期维护的关键选择使用 ADR，普通实现细节不建 ADR；实现偏离已确认设计时，先更新方案和执行步骤。

`iOSFlowRecords/` 是工作目录中可直接查看的运行状态，不属于可更新的 `.agents/skills/ios-workflow/` 规则目录。是否纳入版本控制由团队自行决定；本示例仓库选择跟踪该目录，以便共享需求、项目顺序和测试证据，接入其他工作目录时可按团队策略忽略。
