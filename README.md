# iOS AI Workflow

一套面向 Codex 的仓库级 iOS Skill，采用官方 `.agents/skills` 结构，不依赖专用 CLI。

## 推荐目录结构

工作流只提供 iOS 规则、模板和脚本。业务项目拥有自己的需求、状态和证据，跨设备时随项目同步。

```text
<业务项目根目录>/
├── App/                         实际 iOS 源码与工程
├── .agents/skills/ios-workflow/  接入的工作流规则，不写运行记录
└── .ios-workflow/
    ├── sources/                 需求原文副本、来源与版本
    ├── generation/              首次生成配置，后续不核对
    ├── requirements/            需求档案、方案与变更
    ├── index.jsonc              当前活动摘要
    ├── history.jsonc            项目执行历史
    ├── progress.json            验收项与证据映射
    ├── handoff.md               跨设备交接
    ├── tests/                   计划及报告
    ├── evidence/                可同步的轻量证据
    └── artifacts/               日志、构建等大型产物，Git 忽略
```

首次生成时先在目标项目内建立 `.ios-workflow/`；`allow_project_records=True` 允许生成器保留该目录，仍拒绝覆盖已有业务文件。如工作流集中安装在另一目录，运行记录也只写业务项目。规则仓库里的历史记录保留为旧版只读资料，不在其中继续登记业务项目进度。

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

Skill 入口固定为 `.agents/skills/ios-workflow/SKILL.md`，包含 YAML `name` 和 `description`；`agents/openai.yaml` 提供界面元数据。仓库只有一个可发现的 Skill，内部 `references/` 是按需规则与检查表，`assets/templates/` 是产物模板，不需要各自增加 `SKILL.md` 或伪装成独立 Skill。

## 团队分发

版本 Tag 推送后，GitHub Actions 会先运行完整 Python 测试和五组 macOS 无签名编译检查（覆盖三种技术组合及 Swift 5/6），均通过后再生成 `ios-workflow-<版本>.zip` 和 SHA-256 校验文件并创建 GitHub Release。分发包包含 `.agents/skills/ios-workflow/`、最外层配置示例与字段说明、`AGENTS.md` 示例、版本标记和接入说明，不包含本仓库的 `.ios-workflow/` 运行历史。

团队成员在临时目录解压发布包，将 `.agents/skills/ios-workflow/` 放入业务仓库的相同路径；没有 `AGENTS.md` 时使用包内示例，已有该文件时只合并适用规则。业务仓库应提交这些文件，使全体成员使用同一版本。详细步骤见 [`distribution/INSTALL.md`](distribution/INSTALL.md)。

维护者先按[生成工程编译检查](docs/generated-project-checks.md)验证生成源码及测试 target，再本地生成并检查分发包：

```bash
python3 scripts/build_distribution.py --version 6.3.1 --output dist
```

## 按任务加载，减少 Token

完整入口只负责路由，不再要求每次任务读取所有配置和规范：

- 明确的低风险任务在上下文形成需求卡和简要方案；范围不清或需要正式产物时才加载需求、设计规范和对应模板。
- 需求可执行后按风险加载技术设计规范；小改动写精简方案，高风险或跨模块改动才加载完整模板。
- 追踪按创建、恢复、验收、同步分模块。恢复脚本只输出当前需求的分页摘要；摘要不足再按章节读取档案，不扫描全部历史。
- 普通业务修改只加载核心规范和当前使用的 Swift 或 Objective-C 规范。
- 新生成代码额外加载生成与注释规范。
- UI 任务额外加载 UI 规范和 DesignTokens。
- 三方库或编译任务加载依赖规范。
- 测试计划、执行或失败分析加载测试规范；证据键未变化时复用结果，flaky 确认最多额外复跑一次。
- Archive、TestFlight、App Store 审核或版本发布加载发布分发规范；上传、加测试人员、送审和开始发布只在用户明确要求时执行。
- 新项目先整理项目配置实例；项目复制示例并修改，不自动补值，仅加载相关生成规则。
- 提交、推送或 review 先加载轻量门禁；订阅、打点和发布分发模块只在 diff 涉及时加载。
- README、架构说明和历史记录不属于日常任务的必读上下文。
- 已经进入当前上下文的入口或规则文件不会重复读取；组合任务先对文件路径去重。

组合任务加载对应规则的并集。不要为了“可能有用”预读其他文件；命令成功时仅保留摘要，失败时仅保留相关日志。当前 diff、配置和依赖未变化时，可以复用本任务已经成功的安装、构建、测试和静态检查证据。

维护者可用[模块加载与 Token 评测](docs/module-loading-evaluation.md)导入真实工具事件，或显式运行单个只读探针，检查多余加载、重复读取和实际用量。九个场景的期望与运行结果分开保存；无法观察的操作标为无法判定。该工具不进入日常 Skill 路由，不在普通测试中启动模型，也不把会话总用量当作本 Skill 的节省比例。

## 从需求文档开始

你可以直接说：“按这份需求文档创建 iOS 项目，并支持跨设备继续开发。”不要求文档使用固定格式；客户端读取 Markdown、文本、PDF、Word 或表格，提取业务需求和 iOS 约束。无法读取的内容明确列为缺失。

1. 记录文档来源和版本，逐项判断与通用规则或工具能力的差异。项目明确需求优先于示例和通用建议；内部矛盾或不可实现的要求单独处理，不静默改需求。
2. 先确认项目阶段。首次建项才由客户端按需求和项目技术决定保存完整配置到 `.ios-workflow/generation/`；最外层 `project.example.jsonc` 仅作结构参考，不自动补值。已有工程收到新版本需求时直接迭代，跳过配置与生成。
3. 建立需求及验收追踪，首次建项再生成工程。后续开发依据实际工程及当前需求，不重新核对初始配置。
4. 每个验收项保存来源、实现、测试和证据。编写代码不等于验证通过；缺失证据标记待验证，不推断完成。

详见 [需求导入规范](.agents/skills/ios-workflow/references/standards/requirement-intake.md)、[首次配置规范](.agents/skills/ios-workflow/references/standards/project-configuration.md) 和 [NimbleFive 对照示例](docs/configuration-samples/nimblefive/README.md)。本仓库修改和测试工作流，不因此开发该 App。

## 规则与检查文件

- [`requirements.md`](.agents/skills/ios-workflow/references/standards/requirements.md)：编码前的目标、范围、验收标准、影响和完成定义。
- [`requirement-lifecycle.md`](.agents/skills/ios-workflow/references/standards/requirement-lifecycle.md)：需求状态和模块索引；创建、恢复、验收、同步分别按需读取。
- [`technical-design.md`](.agents/skills/ios-workflow/references/standards/technical-design.md)：编码前的设计分级、方案内容、ADR 和变更规则。
- [`project-generation.md`](.agents/skills/ios-workflow/references/standards/project-generation.md)：配置校验、项目生成顺序、支持组合和验证要求。
- [`testing.md`](.agents/skills/ios-workflow/references/standards/testing.md)：测试分层、最小矩阵、证据复用、失败分类和 flaky test 处理。
- [`release-distribution.md`](.agents/skills/ios-workflow/references/standards/release-distribution.md)：Archive、签名、TestFlight、App Store 审核、发布监控和热修复规则。
- [`templates/`](.agents/skills/ios-workflow/assets/templates)：需求、设计、追踪、测试与发布产物模板。
- [`code-core.md`](.agents/skills/ios-workflow/references/standards/code-core.md)：通用命名、架构、日志、隐私和测试基线。
- [`code-swift.md`](.agents/skills/ios-workflow/references/standards/code-swift.md)：仅 Swift 项目加载的语言规则。
- [`code-objc.md`](.agents/skills/ios-workflow/references/standards/code-objc.md)：仅 Objective-C 或混编项目按需加载的语言规则。
- [`code-generation.md`](.agents/skills/ios-workflow/references/standards/code-generation.md)：生成代码和中文注释等级。
- [`dependencies.md`](.agents/skills/ios-workflow/references/standards/dependencies.md)：依赖管理、精确版本、安装、更新和编译。
- [`ui-style.md`](.agents/skills/ios-workflow/references/standards/ui-style.md) 与 [配置示例中的 DesignTokens](distribution/project.example.jsonc)：UI、可访问性、本地化和设计参数。
- [`checklists/`](.agents/skills/ios-workflow/references/checklists)：提交、推送、review 和条件专项门禁。
- [`project_generation.py`](.agents/skills/ios-workflow/scripts/project_generation.py)：Codex 内部调用的配置校验、项目骨架、DesignTokens、XcodeGen 和依赖准备模块，不提供面向团队成员的 CLI。
- [`test_project_generation.py`](tests/test_project_generation.py)：覆盖支持组合、失败场景和工程生成的自动化测试。
- [`skill-trigger-cases.json`](tests/fixtures/skill-trigger-cases.json)：覆盖应触发、不应触发、显式调用、跨平台边界及中英文提示的 Skill 前向评测语料。
- [`evaluate_module_loading.py`](scripts/evaluate_module_loading.py)：维护者按真实事件核对模块加载及 Token；[场景断言](tests/fixtures/module-loading-cases.json)不代表已完成真实运行。
- [`CHANGELOG.md`](CHANGELOG.md)：工作流规则的集中变更历史。
- [`build_distribution.py`](scripts/build_distribution.py)：生成不含项目运行记录的团队分发压缩包与 SHA-256 校验文件。

修改规则时同步更新 `CHANGELOG.md`，通过 review 后再发布新版本。工作流 ZIP 使用[工作流发布清单](.agents/skills/ios-workflow/references/checklists/workflow-release.md)；业务 App 使用发布分发规范。客户端按实际仓库和任务明确发布对象，不从 CHANGELOG 文件名猜测，也不要求工作流包提供 App Store 或签名资料。

## 示例项目

仓库根目录的 [`WorkflowDemo`](WorkflowDemo/) 是使用本工作流生成并继续开发的真实 UIKit/MVVM 项目，包含计数、设置、12 种语言切换、关于我们、单元测试和 UI 测试，可用于查看工作流交付结果。

## 提交与推送门禁

提交、推送或 review 按当前 diff 和语义影响选择 Checklist：`✅` 通过，`❌` 当前门禁失败，`➖` 未影响或不适用。阶段保存可如实记录未完成和测试失败，提交成功不等于验收通过；宣布完成或发布才要求对应范围全部通过。适用门禁失败时停止并给出处理建议；提交将结果写入正文，仅推送不改写已有提交。账本存在本身不触发全项目核验。

提交后立即推送时，如果受测源码、配置、依赖和测试选择没有变化，推送阶段复用提交时的 Checklist，只检查远端、上游和工作区状态。Git 成功验证只显示必要摘要，不重复回显完整提交正文或 Checklist。

## 在 Codex 中使用

无需安装插件或运行工作流专用命令，直接输入自然语言，例如：

```text
按照当前工作目录中的 iOS 工作流增加设置页面。
使用 Swift、UIKit 和 MVVM 创建首页与语言设置功能。
提交并推送当前修改。
```

第一条适合已有项目功能开发；第二条用于明确项目技术选型；第三条会自动执行提交和推送门禁。

新建项目时 Codex 调用内部生成器，先由客户端提取需求并保存独立配置实例，生成器读取并校验实例，再创建源码、本地化、测试、隐私清单和 XcodeGen 配置；完整配置不会先进入模型上下文。团队成员仍然只需使用自然语言，不需要直接运行 Python 或工作流命令。若配置非法、目标目录已有业务文件、XcodeGen 或依赖工具缺失，流程会停止并说明原因，不会继续编译。

测试任务会先把 Requirement 验收项映射到单元、集成、UI 或专项验证，再选择最小充分的设备和系统矩阵。低风险结果可记录在需求档案；跨模块、高风险或跨会话任务使用 `.ios-workflow/tests/` 中的计划和报告。环境阻塞、真实失败和 flaky test 会分别报告，不会通过无限重试或跳过测试制造通过结果。

发布任务按“预检 → Release 验证 → Archive 与校验 → 导出或上传 → TestFlight → App Store 审核与发布 → 监控和止损”推进。上传成功、构建处理完成、可供测试、审核通过和用户可用分别记录；证书、私钥和 API Key 不进入仓库或日志。没有明确外部动作授权时，工作流停在本地准备或报告阶段。

收到目标明确的低风险任务后，Codex 直接在上下文中整理精简需求卡和 inline brief；范围不清、需要留档或触发完整设计时才加载对应规范。只有关键信息会改变方案或验收结果时才询问；文档执行或跨设备任务会在业务项目内保留需求追踪，普通低风险维护不强制建档。

## 需求执行与跨设备恢复

执行整份需求文档或跨设备任务必须在业务项目内建档；普通低风险单轮维护仍可用上下文需求卡。需求分解成稳定验收项，区分待实现、实现中、已实现、已验证、阻塞、延期和取消；仅当前范围全部验收成立后才可标记需求完成。

跨设备时同步业务项目 Git 中的源码、需求、进度、交接及轻量证据。切换前保存当前步骤、下一动作、阻塞、受测输入和环境。新设备核对远端/分支/HEAD、工作区、文件和哈希后恢复；未推送、未同步、冲突、丢失证据或环境不可用均明确报告，不猜测旧对话内容。

客户端可调用以下内部模块，团队成员仍使用自然语言：

| 模块 | 作用 |
| --- | --- |
| `resume_context.py` | 输出当前需求的有界摘要并核对记录关联；明确分页、缺项与截断 |
| `tracking_state.py` | 只读核对当前需求的索引、台账、验收状态及档案头部，发现终态未清、遗漏记录和状态矛盾；不读无关历史证据 |
| `change_scope.py` | 按路径线索和已确认语义影响选择相关检查，不直接判断通过 |
| `progress_validation.py` | 按相关需求/验收项核对路径、成功证据、实际哈希、环境与时间；全项目检查需显式选择 |
| `evidence_tools.py` | 采集实际证据和输入哈希、iOS 测试环境指纹；复用比较返回 matched/stale/unknown |
| `project_generation.py` | 首次配置诊断一次汇总独立问题，不自动填值 |

结构验证和哈希一致不证明业务正确，也不保证永不产生 AI 错误；当前证据必须实际覆盖验收条件。未知环境、缺失证据、失败结果或变更输入不能充当可复用的成功结果。

用户授权的 Git 提交/推送用于同步；仅本地完成不等于其他设备已可继续。大型日志和构建产物存项目内 `artifacts/` 并忽略，需要另行共享或重新验证。不要忽略整个 `.ios-workflow/`，不要用另一台设备的绝对路径充当可用证据。

## 技术方案与架构设计

需求分析完成后，Codex 在编码前选择设计等级：纯维护可标记 `not_required`；单模块低风险改动，以及不改变公共契约的简单新增页面或内部模块使用 `brief`；跨模块、公共接口、数据结构、依赖、并发、迁移、隐私安全或订阅支付变化使用 `full` 模板。“新增模块”本身不自动升级为完整设计。

设计状态只有 `pending`、`approved`、`not_required`。只有设计通过或明确不需要设计时才能进入实现。影响长期维护的关键选择使用 ADR，普通实现细节不建 ADR；实现偏离已确认设计时，先更新方案和执行步骤。
