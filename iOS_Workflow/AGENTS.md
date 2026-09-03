# iOS AI Workflow Instructions

本文件位于 `<工作目录>/iOS_Workflow/`，工作目录名称由使用者自行决定；相对路径以 `iOS_Workflow/` 为基准。先判断任务类型，合并并去重对应规则；每个文件每个任务最多读取一次。

## 通用要求

1. 用户明确要求优先；冲突时说明。保持项目已有语言、UI、架构和模块边界。
2. 修改后运行最小相关验证。证据以 diff、配置和依赖锁定状态为键；键未变化则复用，变化才重跑。生成器变更运行 `python3 -m unittest discover -s tests -v`。
3. 成功命令只报告目标、状态和必要摘要；失败只保留相关日志。Git 验证不回显完整提交、tag 或 Checklist 正文。
4. 工作流规则变更同步更新 `CHANGELOG.md`。

## 路由

- 新项目：`config/defaults.jsonc`、`standards/code-core.md`、所选语言规范、`standards/code-generation.md`、`standards/ui-style.md`、`config/design-tokens.jsonc`、`standards/dependencies.md`。
- 新增手写代码：核心规范、所用语言规范、`standards/code-generation.md`。
- 业务修改、重构、修复：核心规范和所用语言规范；新增代码再加载生成规范。
- UI：核心规范、所用语言规范、`standards/ui-style.md`、`config/design-tokens.jsonc`；新增代码再加载生成规范。
- 依赖或编译：`standards/dependencies.md`；修改源码时再加载对应代码规范。
- 提交、推送、review：`checklists/pre-commit-review.md`，并按其条件加载检查模块。
- 文档或工作流：只读取直接相关文件。

核心规范为 `standards/code-core.md`；语言规范按实际代码选择 `standards/code-swift.md`、`standards/code-objc.md` 或两者。README、`docs/` 和历史记录不是日常必读上下文。
