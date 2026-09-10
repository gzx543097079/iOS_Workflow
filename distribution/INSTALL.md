# 团队接入

1. 在临时目录解压发布包，通过 `IOS_WORKFLOW_VERSION` 确认版本，并确认其中包含 `.agents/skills/ios-workflow/`、`AGENTS.ios-workflow.example.md`、最外层配置示例及字段说明、版本标记和本说明。
2. 将 `.agents/skills/ios-workflow/` 复制到业务仓库根目录的相同路径；更新已有版本时先检查差异，再替换该 Skill 目录。
3. 业务仓库没有 `AGENTS.md` 时，将示例改名为 `AGENTS.md`；已有该文件时只合并适用规则，不覆盖项目约定。
4. 在 Codex 中打开业务仓库根目录，并提交 `.agents/skills/ios-workflow/` 与 `AGENTS.md`，让团队成员使用同一版本。

`.ios-workflow/` 是各业务项目运行时按需创建的状态目录，不包含在发布包中，也不要从工作流仓库复制历史记录。

## 首次生成项目

解压后直接在最外层找到 `project.example.jsonc` 和 `PROJECT_CONFIGURATION.md`。复制示例，按项目需求修改，保存为自己的配置（例如 `NimbleFive.project.jsonc`），再把该文件路径交给工作流首次生成工程。配置放在生成目标目录之外，目标目录必须为空。

该配置只用于首次生成，缺项时明确报错，不自动补全。生成完成后可归档或删除输入配置；后续版本直接维护实际工程，不再读取或核对生成配置。已有项目接入只需上述 Skill 接入步骤，不需要配置实例。
