# iOS AI Workflow Instructions

本文件通常位于 `Workspace/iOS_Workflow/AGENTS.md`，以下相对路径均以 `iOS_Workflow/` 为基准。先判断任务类型，只读取对应规则；组合任务读取各类型规则的并集，不要预先加载无关文档。

## 通用要求

1. 用户当前明确要求优先于默认配置；发现冲突时说明冲突。
2. 保持项目已有语言、UI 框架、架构和模块边界，不无理由切换技术方案。
3. 修改后运行最小相关测试；修改生成器时运行 `python3 -m unittest discover -s tests -v`。
4. 修改工作流规则时同步更新 `CHANGELOG.md`。

## 按任务读取

- 新建 iOS 项目：读取 `config/defaults.jsonc`、`standards/code-core.md`、`standards/code-generation.md`、`standards/ui-style.md`、`config/design-tokens.jsonc`、`standards/dependencies.md`；若仓库提供生成器，优先使用生成器。
- 新增手写代码：读取 `standards/code-core.md` 和 `standards/code-generation.md`。
- 修改业务逻辑、重构或修复缺陷：读取 `standards/code-core.md`；若新增代码，再读取 `standards/code-generation.md`。
- 新增或修改 UI：读取 `standards/code-core.md`、`standards/ui-style.md` 和 `config/design-tokens.jsonc`；若新增代码，再读取 `standards/code-generation.md`。
- 引入、安装、更新三方库或执行编译：读取 `standards/dependencies.md`；仅在同时修改源码时读取对应代码规范。
- 提交、推送或 review：读取 `checklists/pre-commit-review.md`，再按其路由读取检查模块。出现任一 `❌` 时停止提交或推送并提示用户。
- 仅修改文档或工作流：只读取与目标直接相关的文件，不自动加载代码、UI、依赖或 checklist 规则。

README 和 `docs/` 用于团队使用说明，不属于每次任务的必读上下文。
