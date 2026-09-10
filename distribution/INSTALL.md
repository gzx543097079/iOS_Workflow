# 团队接入

1. 在临时目录解压发布包，通过 `IOS_WORKFLOW_VERSION` 确认版本，并确认其中只有 `.agents/skills/ios-workflow/`、`AGENTS.ios-workflow.example.md`、版本标记和本说明。
2. 将 `.agents/skills/ios-workflow/` 复制到业务仓库根目录的相同路径；更新已有版本时先检查差异，再替换该 Skill 目录。
3. 业务仓库没有 `AGENTS.md` 时，将示例改名为 `AGENTS.md`；已有该文件时只合并适用规则，不覆盖项目约定。
4. 在 Codex 中打开业务仓库根目录，并提交 `.agents/skills/ios-workflow/` 与 `AGENTS.md`，让团队成员使用同一版本。

`.ios-workflow/` 是各业务项目运行时按需创建的状态目录，不包含在发布包中，也不要从工作流仓库复制历史记录。
