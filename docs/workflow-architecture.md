# 工作流架构

## 目标

这套工作流把“创建项目”“团队规则”“AI 上下文”拆成独立、可迁移的模块。仓库本身不绑定某个 App，也不依赖某一种 AI 产品。

## 模块

```text
iOS AI Workflow
├── bin/iosflow                 项目生成与校验入口
├── config/defaults.jsonc       新项目默认技术选型与工程设置
├── config/design-tokens.jsonc  UI 参数的单一事实来源
├── standards/code-style.md     人可读代码规范
├── standards/ui-style.md       人可读 UI 规范
├── AGENTS.md                   AI 协作入口
└── tests/                      生成器回归测试
```

## 生成流程

1. CLI 读取默认配置，命令行参数可逐项覆盖，包括跟随系统或固定语言的首次启动策略。
2. 校验技术组合；SwiftUI 仅接受 Swift。
3. 根据语言、UI 与架构写入最小可运行源码。
4. 按 1–4 级中文注释配置为源码、单元测试及 UI 测试增加对应深度的自然语句说明，不生成文件元数据头或分类标签。
5. 从中央 `design-tokens.jsonc` 生成对应 Swift 或 Objective-C token 代码。
6. 将语言策略与默认本地化写入 `Info.plist` 和 `workflow.json`，供 App 运行时读取。
7. 将当前规范快照复制进新项目的 `Standards/`。
8. 输出 XcodeGen 的 `project.yml`；本机可用时自动生成 `.xcodeproj`。

## 可迁移性

- 核心生成只需 Python 3 标准库。
- 仓库可以复制、作为 Git submodule 引用，或发布到团队内部模板仓库。
- Xcode 工程文件由声明式配置生成，不把用户机器路径写进模板。
- 规范和 token 均为文本文件，可代码评审、打 tag、回滚和分支演进。

## 推荐演进路线

- v1：当前范围，项目骨架 + 代码/UI 规范 + 校验测试。
- v1.1：增加 Coordinator、Clean Architecture 等团队确认后的模板。
- v1.2：把网络、日志、存储、依赖注入做成可选 feature packs。
- v1.3：接入 CI 模板、SwiftLint/SwiftFormat 固定版本和规范迁移命令。
- v2：当团队规模需要时，把 CLI 打包为 Swift 可执行文件或内部 Homebrew Formula。
