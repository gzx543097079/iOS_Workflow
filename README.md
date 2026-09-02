# iOS AI Workflow

一套面向 Codex 桌面端的文件化 iOS 团队工作流，不依赖专用 CLI。

## 推荐目录结构

```text
Workspace/
├── AGENTS.md
├── MyProject/
└── iOS_Workflow/
    ├── AGENTS.md
    ├── README.md
    ├── LICENSE
    ├── config/
    ├── standards/
    ├── checklists/
    └── docs/
```

- `Workspace/AGENTS.md`：Codex 自动读取的轻量入口，负责指向外部工作流。
- `Workspace/MyProject/`：团队成员的业务项目，使用自己的 Git 仓库。
- `Workspace/iOS_Workflow/`：独立维护和更新的工作流仓库。

## 接入方法

1. 在本地建立一个共同的 `Workspace/` 目录。
2. 将工作流仓库放在 `Workspace/iOS_Workflow/`。
3. 将业务项目放在 `Workspace/MyProject/`，项目名称可以自行调整。
4. 在 Workspace 根目录创建 `Workspace/AGENTS.md`：

   ```md
   # 项目工作流入口

   开始任何编码、提交或 review 工作前，必须读取并遵循：

   - `iOS_Workflow/AGENTS.md`

   工作流中引用的相对路径以 `iOS_Workflow/` 为基准。
   项目自身明确约定和用户当前要求具有更高优先级。
   ```

5. 在 Codex 桌面端打开整个 `Workspace/`，直接提出项目需求。

Codex 会自动读取 Workspace 根目录的 `AGENTS.md`。该入口要求 Codex 继续读取 `iOS_Workflow/AGENTS.md`，再加载配置、规范和 Checklist。一个入口可以服务 Workspace 下的多个业务项目；工作流升级后入口路径保持不变。

注意：

- 文件名必须是 `AGENTS.md`，不能写成 `AGENTS` 或 `AGDGENTS.md`。
- 如果工作流目录不是 `iOS_Workflow`，需要同步修改 Workspace 入口中的相对路径。
- 团队成员更新 `iOS_Workflow` 时不会直接修改业务项目的 Git 历史；建议按版本 tag 固定团队使用的工作流版本。
- 原始 `AGENTS.md` 始终保留在 `iOS_Workflow/` 中；Workspace 根目录仅保存轻量入口内容。

## 默认配置

默认配置位于 [`config/defaults.jsonc`](config/defaults.jsonc)，部署后对应 `Workspace/iOS_Workflow/config/defaults.jsonc`：

- 开发语言：Swift
- UI：UIKit
- 架构：MVVM
- 默认语言策略：跟随系统
- 默认本地化：英语
- 中文注释等级：3
- 依赖管理：CocoaPods

用户在当前任务中明确指定的语言、UI、架构、本地化或注释设置优先于默认配置。

## 规范与检查

- [`code-style.md`](standards/code-style.md)：Swift、Objective-C、架构、日志、隐私和测试规范。
- [`ui-style.md`](standards/ui-style.md)：布局、DesignTokens、可访问性和本地化规范。
- [`pre-commit-review.md`](checklists/pre-commit-review.md)：提交和 review 前的通用、订阅及数据打点检查。

修改规范时应同步更新对应文件底部的 changelog，并通过代码 review 后再发布新版本。

## 在 Codex 中使用

打开业务项目后，可以直接提出自然语言需求，例如：

```text
按照 Workspace 的 AGENTS.md 和 iOS 工作流增加设置页面。
使用 Swift、UIKit 和 MVVM 创建首页与语言设置功能。
提交前按照工作流 Checklist 检查当前修改。
```

无需安装插件或运行工作流专用命令。
