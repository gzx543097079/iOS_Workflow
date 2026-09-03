# 工作流架构

## 目标

工作流以文本文件约束 Codex 的项目生成、编码和 review 行为，不依赖专用 CLI，也不在业务项目中创建独立 Git 仓库。运行时入口保持精简，仅按当前任务载入必要规则。

## 部署结构

```text
<工作目录>/
├── AGENTS.md                         指向外部工作流的轻量入口
├── MyProject/                        业务项目及其 Git 仓库
└── iOS_Workflow/                     工作流 Git 仓库
    ├── AGENTS.md                     按任务分流的工作流入口
    ├── CHANGELOG.md                  集中的规则变更历史
    ├── config/
    │   ├── defaults.jsonc            仅新项目读取的默认选项
    │   └── design-tokens.jsonc       UI 参数来源
    ├── standards/
    │   ├── code-core.md              核心代码规则
    │   ├── code-swift.md             Swift 语言规则
    │   ├── code-objc.md              Objective-C 语言规则
    │   ├── code-generation.md        生成代码与注释规则
    │   ├── dependencies.md           三方库与编译规则
    │   └── ui-style.md               UI 规范
    ├── checklists/
    │   ├── pre-commit-review.md      门禁与条件路由
    │   ├── core.md                   通用检查
    │   ├── subscription.md           订阅专项检查
    │   └── analytics.md              打点专项检查
    └── docs/                         非运行时说明
```

## 加载流程

1. Codex 打开用户选择的工作目录后读取根部轻量 `AGENTS.md`，再进入 `iOS_Workflow/AGENTS.md`；工作目录名称不限。
2. 工作流入口判断任务类型，只加载对应规则；组合任务取规则并集并按文件路径去重，已进入上下文的文件不再读取。
3. 用户明确选项覆盖默认配置，业务项目自身约定优先于通用工作流。
4. 普通代码、生成代码、UI、依赖和新项目分别走独立路由；Swift 与 Objective-C 规范也按实际语言选择。
5. 提交、推送或 review 时加载门禁和通用检查；检查 diff 后，只有影响订阅或打点时才加载专项模块。
6. 存在 `❌` 时阻止提交或推送；通过时把结果写入提交备注或推送结果。
7. diff、配置和依赖未变化时复用本任务的安装、构建和测试证据；提交后立即推送只进行远端增量检查。

README、`docs/` 和 `CHANGELOG.md` 供接入、维护与追溯使用，不自动进入日常编码上下文。成功命令只输出摘要，失败时保留定位所需的相关日志；Git 验证不重复输出完整提交或 Checklist 正文。

## Git 边界

`iOS_Workflow/` 和业务项目是两个同级目录，可以分别使用独立 Git 仓库。轻量入口位于二者共同的工作目录根部；团队切换工作流版本 tag 后，入口路径保持不变。
