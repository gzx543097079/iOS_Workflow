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

生成新的手写代码时，Codex 会直接按照 `comment_level` 添加中文注释。默认第 3 级会说明页面用途、业务自定义方法、Model 用途和复杂实现思路；系统方法、继承方法、生命周期及代理/数据源回调不生成注释，也不生成文件元数据或“类型职责”“方法职责”等标签。该规则不要求生成完成后再扫描或批量补写已有代码。

`dependency_manager` 会在生成阶段落实为对应的项目配置：`pod` 使用 `Podfile`，`spm` 使用 Xcode/`project.yml` 的 Swift Package 引用，`carthage` 使用 `Cartfile`，`none` 不预设依赖管理文件。工作流不会为了展示依赖管理方式而虚构项目不需要的三方库。

所有直接三方库必须指定完整的精确版本号，例如 `1.2.3`。禁止使用大于、小于、兼容范围、通配符、分支、commit、`latest` 或省略版本。CocoaPods 使用固定版本字符串，Swift Package Manager 使用 Exact Version，Carthage 使用 `==`。

依赖操作会在以下阶段执行：新项目创建后安装依赖；明确修改库版本后更新指定依赖；每次编译前按当前依赖管理方式执行安装、解析或 bootstrap。依赖操作失败时停止编译并提示用户，不会跳过错误继续构建。详细规则见 [`code-style.md`](standards/code-style.md)。

## 规范与检查

- [`code-style.md`](standards/code-style.md)：Swift、Objective-C、架构、日志、隐私和测试规范。
- [`ui-style.md`](standards/ui-style.md)：布局、DesignTokens、可访问性和本地化规范。
- [`pre-commit-review.md`](checklists/pre-commit-review.md)：提交和 review 前的通用、订阅及数据打点检查。

修改规范时应同步更新对应文件底部的 changelog，并通过代码 review 后再发布新版本。

## 提交与推送门禁

当用户要求提交代码、推送到远端，或者同时提交并推送时，Codex 必须自动执行 [`pre-commit-review.md`](checklists/pre-commit-review.md)，无需用户再次要求。

- `✅` 表示检查通过。
- `❌` 表示检查不通过。
- `➖` 表示本次代码未影响该项或该项不适用，并需要说明原因。

只要存在一个 `❌`，Codex 就必须停止提交或推送，向用户展示完整结果，并明确提示失败项和建议处理方式。所有适用项通过后才允许继续：提交操作把 Checklist 写入提交备注；仅推送操作不改写已有提交，而是在推送结果中输出 Checklist。

如果订阅、数据打点或 UI 等整个模块均未受本次代码影响，可以使用一条 `➖` 合并说明该模块，不需要制造无意义的逐项通过结果。

## 在 Codex 中使用

打开业务项目后，可以直接提出自然语言需求，例如：

```text
按照 Workspace 的 AGENTS.md 和 iOS 工作流增加设置页面。
使用 Swift、UIKit 和 MVVM 创建首页与语言设置功能。
提交前按照工作流 Checklist 检查当前修改。
```

无需安装插件或运行工作流专用命令。
