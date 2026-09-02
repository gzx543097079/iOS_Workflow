# iOS AI Workflow Instructions

本目录中的所有 AI 编码工作都应遵循以下顺序：

1. 先阅读 `standards/code-style.md`、`standards/ui-style.md` 和 `config/defaults.jsonc`。
2. 新建 iOS 项目时使用 `./bin/iosflow new`，不要手工拼装 `.xcodeproj`。
3. 保持用户选定的语言、UI 框架和架构，不得无理由混用另一套技术。
4. 新增 UI 时优先复用 `DesignTokens`，不要在业务页面散落颜色、间距、字号与圆角常量。
5. 新增业务模块时遵守生成项目中 `Features/<Feature>` 的边界。
6. 修改完成后运行最小相关测试；修改生成器时必须执行 `python3 -m unittest discover -s tests -v`。
7. 执行 Git 提交或代码 review 前，必须阅读 `checklists/pre-commit-review.md` 并运行 `./bin/iosflow checklist . --purpose commit` 或 `--purpose review`；未通过时不得继续提交或给出 review 结论。
8. 若需求与规范冲突，明确指出冲突并以用户当前明确要求为准，同时建议是否更新规范。

规范是可演进的团队约定，不是不可变规则。修改规范时应同步更新文件底部 changelog。
