# iOS AI Workflow Instructions

本文件保留在 `Workspace/iOS_Workflow/AGENTS.md`。Workspace 根目录的轻量 `AGENTS.md` 指向本文件；以下相对路径均以 `iOS_Workflow/` 为基准：

1. 先阅读 `standards/code-style.md`、`standards/ui-style.md` 和 `config/defaults.jsonc`。
2. 新建或修改 iOS 项目时，以默认配置和规范文件为基线；用户明确指定的选项优先。
3. 保持用户选定的语言、UI 框架和架构，不得无理由混用另一套技术。
4. 新增 UI 时优先复用 `DesignTokens`，不要在业务页面散落颜色、间距、字号与圆角常量。
5. 新增业务模块时遵守生成项目中 `Features/<Feature>` 的边界。
6. 修改完成后运行项目中最小相关的构建、测试和静态检查。
7. 执行 Git 提交或代码 review 前，必须阅读并逐项完成 `checklists/pre-commit-review.md`；存在未通过或未说明的检查项时，不得继续提交或给出 review 结论。
8. 若需求与规范冲突，明确指出冲突并以用户当前明确要求为准，同时建议是否更新规范。

规范是可演进的团队约定，不是不可变规则。修改规范时应同步更新文件底部 changelog。
