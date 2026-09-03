# 工作流架构

## 目标

工作流以文本文件约束 Codex 的项目生成、编码和 review 行为，不依赖专用 CLI，也不在业务项目中创建独立 Git 仓库。运行时入口保持精简，仅按当前任务载入必要规则。

## 部署结构

```text
<工作目录>/
├── AGENTS.md                         指向外部工作流的轻量入口
├── MyProject/                        业务项目及其 Git 仓库
├── iOSFlowRecords/
│   ├── index.jsonc                   活动需求索引
│   ├── requirements/                 单个需求档案
│   └── projects/                     项目需求执行顺序
└── iOS_Workflow/                     工作流 Git 仓库
    ├── AGENTS.md                     按任务分流的工作流入口
    ├── CHANGELOG.md                  集中的规则变更历史
    ├── config/
    │   ├── defaults.jsonc            仅新项目读取的默认选项
    │   └── design-tokens.jsonc       UI 参数来源
    ├── standards/
    │   ├── requirements.md           需求分析与任务定义
    │   ├── requirement-lifecycle.md  状态、恢复与 Git 关联
    │   ├── technical-design.md       技术设计分级与架构方案
    │   ├── project-generation.md     项目生成顺序与支持范围
    │   ├── code-core.md              核心代码规则
    │   ├── code-swift.md             Swift 语言规则
    │   ├── code-objc.md              Objective-C 语言规则
    │   ├── code-generation.md        生成代码与注释规则
    │   ├── dependencies.md           三方库与编译规则
    │   └── ui-style.md               UI 规范
    ├── templates/
    │   ├── requirements/             Feature 与 Bug 需求模板
    │   ├── design/                   Feature、Bug Fix 与 ADR 模板
    │   └── tracking/                 索引、需求档案与项目台账模板
    ├── checklists/
    │   ├── pre-commit-review.md      门禁与条件路由
    │   ├── core.md                   通用检查
    │   ├── subscription.md           订阅专项检查
    │   ├── analytics.md              打点专项检查
    │   ├── technical-design.md       技术设计检查
    │   ├── project-generation.md     项目生成专项检查
    │   └── requirement-traceability.md 需求追溯检查
    ├── tools/
    │   └── project_generation.py     内部项目生成与依赖准备模块
    ├── tests/
    │   └── test_project_generation.py 生成器自动化测试
    └── docs/
        └── adr/                      工作流长期技术决策
```

## 加载流程

1. Codex 打开用户选择的工作目录后读取根部轻量 `AGENTS.md`，再进入 `iOS_Workflow/AGENTS.md`；工作目录名称不限。
2. 新功能和缺陷先形成最小需求卡；关键信息不足时才加载对应模板或向用户确认。
3. 按范围和风险选择 `not_required`、`brief` 或 `full` 技术设计；设计通过后生成最终步骤。
4. 需要保存或执行时在可见的 `iOSFlowRecords/` 创建档案和步骤；首次执行时写入项目台账并分配固定顺序号。继续任务只加载索引及活动需求。
5. 工作流入口判断任务类型，只加载对应规则；组合任务取规则并集并按文件路径去重，已进入上下文的文件不再读取。
6. 用户明确选项覆盖默认配置，业务项目自身约定优先于通用工作流。
7. 普通代码、生成代码、UI、依赖和新项目分别走独立路由；新项目先校验配置，再由内部生成器创建三种受支持的工程组合，Swift 与 Objective-C 规范按实际语言选择。
8. 提交、推送或 review 时加载门禁和通用检查；按 diff 加载技术设计、项目生成、订阅、打点和需求追溯模块。
9. 存在 `❌` 时阻止提交或推送；通过时把结果写入提交备注或推送结果，并更新需求记录。
10. diff、配置和依赖未变化时复用本任务的安装、构建和测试证据；提交后立即推送只进行远端增量检查。

README、`docs/` 和 `CHANGELOG.md` 供接入、维护与追溯使用，不自动进入日常编码上下文。成功命令只输出摘要，失败时保留定位所需的相关日志；Git 验证不重复输出完整提交或 Checklist 正文。

## Git 边界

`iOS_Workflow/` 和业务项目是两个同级目录，可以分别使用独立 Git 仓库。轻量入口和 `iOSFlowRecords/` 位于共同工作目录根部；团队切换工作流版本 tag 后，规则入口和运行记录路径保持不变。
