# 工作流架构

## 目标

工作流以文本文件约束 Codex 的项目生成、编码和 review 行为，不依赖专用 CLI，也不在业务项目中创建独立 Git 仓库。

## 部署结构

```text
Workspace/
├── AGENTS.md                         指向外部工作流的轻量入口
├── MyProject/                        业务项目及其 Git 仓库
└── iOS_Workflow/                     工作流 Git 仓库
    ├── AGENTS.md                     工作流原始入口文件
    ├── README.md                     接入与使用说明
    ├── LICENSE                       开源协议
    ├── config/
    │   ├── defaults.jsonc            默认技术选型与工程设置
    │   └── design-tokens.jsonc       UI 参数来源
    ├── standards/
    │   ├── code-style.md             代码规范
    │   └── ui-style.md               UI 规范
    ├── checklists/                   提交与 review 检查
    └── docs/                         工作流架构说明
```

## 加载流程

1. Workspace 根目录保留一个轻量 `AGENTS.md`，指向 `iOS_Workflow/AGENTS.md`。
2. Codex 桌面端打开整个 Workspace，自动读取根目录的 `AGENTS.md`。
3. Workspace 入口要求 Codex 读取工作流原始入口，并以 `iOS_Workflow/` 为基准加载默认配置和规范文件。
4. 用户明确指定的技术选型覆盖默认配置，业务项目自身约定优先于通用工作流。
5. Codex 按项目现有技术、模块边界和 DesignTokens 完成修改。
6. 提交或 review 前，Codex 读取并逐项完成工作流中的 `checklists/pre-commit-review.md`。

## Git 边界

`iOS_Workflow/` 和业务项目是两个同级目录，可以分别使用独立 Git 仓库。轻量入口位于二者共同的 Workspace 根目录；团队切换工作流版本 tag 后，入口继续读取该版本的规则。
