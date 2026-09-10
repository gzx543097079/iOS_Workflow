# 工作流架构

## 目标

工作流主要服务 iOS 项目，以一个仓库级 Skill 提供规则、模板和可导入的 Python 辅助接口，不要求团队成员记忆专用 CLI。用户当前要求与业务项目明确约定优先于通用建议；工作过程中的实际需求、进度和证据属于业务项目。

## 规则与项目记录

工作流源码及发布素材：

```text
iOS_Workflow/
├── AGENTS.md
├── .agents/skills/ios-workflow/
│   ├── SKILL.md                       唯一 Skill 入口与按任务路由
│   ├── agents/openai.yaml             UI 元数据
│   ├── references/
│   │   ├── standards/                通用规范及按任务拆分的追踪规则
│   │   └── checklists/               提交、review、发布与专项检查
│   ├── assets/templates/             通用模板，无业务运行状态
│   └── scripts/                      生成、恢复摘要、证据及检查辅助接口
├── distribution/
│   ├── project.example.jsonc         配置结构示例，不是默认配置
│   ├── PROJECT_CONFIGURATION.md      首次生成字段说明
│   ├── AGENTS.example.md
│   └── INSTALL.md
├── tests/                            工作流、生成器与辅助接口测试
├── CHANGELOG.md
└── docs/                             接入、架构和历史决策说明
```

每个业务项目独立保存执行状态：

```text
MyProject/
├── AGENTS.md                         项目自身约定
├── .agents/skills/ios-workflow/       接入的通用规则，按需安装
├── App/                              实际源码、工程及依赖
└── .ios-workflow/
    ├── sources/                      需求来源或可审阅快照
    ├── generation/project.jsonc      首次生成输入，后续仅为历史资料
    ├── index.jsonc                   一个活动需求的紧凑摘要
    ├── progress.json                 全项目验收状态的唯一机器账本
    ├── requirements/                 需求档案、方案及阶段记录
    ├── history.jsonc                 需求首次执行顺序与当前状态
    ├── handoff.md                    需要交接时保存的恢复入口
    ├── tests/                        测试计划与精简报告
    ├── evidence/                     可随 Git 恢复的必要证据
    ├── transactions/                 追踪更新的候选记录、事务日志和恢复状态
    └── artifacts/                    可忽略的大型构建产物与原始日志
```

所有来源、实现与证据引用均相对于所属业务项目根目录。多个项目不共用运行账本；不根据客户端当前工作目录猜测项目归属。`.ios-workflow/` 是项目内约定，不属于官方 Skill 结构。

## 渐进加载

1. `AGENTS.md` 保留精简项目约束。匹配 iOS 任务或明确调用后加载 `SKILL.md`，组合任务按文件路径合并去重规则。
2. 低风险单轮维护可在上下文形成精简需求卡和 inline brief。执行整份需求文档、跨设备、跨会话、多阶段、跨模块、高风险、共享追踪或明确要求留档时才建立持久记录；执行本身不是建档条件。
3. 新项目先识别文档来源、授权范围、明确技术选择和能力缺口，再保存完整配置实例并生成工程。示例不提供默认值；后续版本遵循实际工程与当前需求，不核对初始生成配置。
4. 追踪规则按当前动作直接读取下表模块，不为恢复任务加载完整生命周期。各文件均为普通 reference，不注册成多个 Skill。

| 动作 | 规则文件 |
| --- | --- |
| 需要选择追踪模块 | [requirement-lifecycle.md](../.agents/skills/ios-workflow/references/standards/requirement-lifecycle.md) |
| 建档、分配稳定需求 ID、登记首次执行 | [tracking-start.md](../.agents/skills/ios-workflow/references/standards/tracking-start.md) |
| 登记验收、核对证据、判定完成 | [tracking-evidence.md](../.agents/skills/ios-workflow/references/standards/tracking-evidence.md) |
| 执行、继续、阻塞、更新阶段摘要 | [tracking-resume.md](../.agents/skills/ios-workflow/references/standards/tracking-resume.md) |
| 跨设备、Git 同步或只查执行历史 | [tracking-sync.md](../.agents/skills/ios-workflow/references/standards/tracking-sync.md) |

恢复时先提取活动摘要和相关验收条目，只有不足时才按章节读取当前需求。进入测试步骤后再读取相关报告；只查询执行顺序时读取 `history.jsonc`。普通代码、UI、依赖、项目生成、测试和发布分别按需加载对应规范。

## 辅助接口与事实边界

| 内部模块 | 作用与边界 |
| --- | --- |
| `project_generation.py` | 显式读取完整首次配置，生成最小工程；不解析自然语言、不补默认值、不代表业务实现完成。 |
| `resume_context.py` | 读取索引、账本、执行台账关联和当前档案头部，分页输出活动摘要并检查状态一致性；不读正文或无关历史证据，不宣称业务完成。 |
| `tracking_state.py` | 只读核对当前需求跨文件的 ID、执行序号及状态关系，明确指出不一致，不自动提升状态。 |
| `tracking_update.py` | 更新选定需求的索引、账本、台账和档案，保留其他需求记录；旧版本与输入变化时停止，按事务日志恢复或显式放弃，不回滚外部编辑。 |
| `progress_validation.py` | 默认按本次相关需求或验收项检查路径、哈希和记录字段，同时保留全账本 ID 唯一性和有效需求关联检查；显式项目健康检查才核验全部账本。 |
| `evidence_tools.py` | 从实际文件和已知环境生成记录并比较变化；不执行测试、不猜测结果、不提升验收状态。 |
| `change_scope.py` | 按变更路径和调用方补充的语义影响选择检查模块；路径线索和检查选择不等于通过。 |

`implemented` 表示已有实际实现，`verified` 需要当前适用的成功证据。哈希、摘要或结构检查不能证明业务正确。证据缺失、过期、环境不明或覆盖不足时明确待核验；不由聊天记忆补造结果。

追踪更新是可恢复的逐文件替换，不是四个文件的一次原子写入。本机协作锁只约束使用同一接口的进程；外部编辑仍需协调，跨设备 Git 冲突仍需按实际记录合并。候选记录和事务日志保留在业务项目，临时核验的源码及证据副本在核验后清理。

## 验证与 Git

验证从本次需求与 diff 选择最小充分范围，前置失败时停止依赖阶段；flaky 最多额外确认复跑一次。相关源码、配置、依赖、环境和测试选择未变化时可复用成功证据，纯文档或运行记录变化不使无关测试失效。

保存阶段进度、确认需求完成和发布采用各自的检查范围。用户要求阶段保存时可以如实提交未完成、未验证或失败记录；不得把阶段提交当作验收通过。只有授权范围和必需验收全部满足时才标记 `done`，Git 交付不重新激活已完成需求。

业务代码、需求来源、档案、账本、交接和必要的精简证据须能随同一项目 Git 恢复，不能忽略整个 `.ios-workflow/`。大型产物可忽略，但不能把另一设备的绝对路径当作可用证据。同步行为遵守用户当前授权；未提交、未推送、离线或远端未核实时明确可见边界。

提交正文使用 `Requirement`、`Steps` 和相关 Checklist 关联。交付状态从 Git 日志、上游和远端引用实时查询，不为回写当前提交 hash 或推送状态制造额外提交。归档与发布材料可在任务范围内准备，上传、提交审核或开始发布须有对应外部动作授权。

## 分发边界

版本发布包包含 `.agents/skills/ios-workflow/`，并在 ZIP 最外层提供 `project.example.jsonc`、字段说明、AGENTS 示例、接入说明和版本标记。业务项目记录、工作流测试和仓库 `docs/` 不进入分发包；运行规则不能依赖发布包之外的历史 ADR。

版本 Tag 触发现有测试、打包、SHA-256 和 GitHub Release 流程。业务项目通过自己的 Git 提交固定接入的 Skill 版本；更新 Skill 不改变项目首次配置或运行状态。README、架构文档和 CHANGELOG 用于接入、维护与追溯，不自动进入日常任务上下文。
