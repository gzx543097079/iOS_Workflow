# 首次生成配置

工作流不设置默认配置。配置示例位于发布包最外层 `project.example.jsonc`，同层 `PROJECT_CONFIGURATION.md` 提供字段说明；仓库源文件位于 `distribution/`，不放在 Skill 内。客户端是 Codex 或其他宿主，本仓库不提供图形配置界面。

## 使用步骤

1. 团队成员解压发布包，在最外层复制 `project.example.jsonc` 为自己的配置，例如 `NimbleFive.project.jsonc`。
2. 按需求修改 `project_name`、完整 `config`、`design_tokens`、`sources` 和 `constraints`。保留示例值属于项目选择，不应声称来自 PRD；脚本不自动加载示例或补值。
3. 配置放在生成目标目录之外，将其路径明确交给生成器。目标必须不存在或为空，生成器不覆盖已有工程。
4. `load_project_instance(path)` 校验首次生成输入；缺失、未知字段、非法组合和不支持的版本拒绝生成。`save_project_instance(path, instance)` 可保存新输入文件，但不覆盖已有文件。
5. 调用 `materialize_project(instance_path, output)` 生成工程并准备依赖；只检查骨架时调用 `generate_project(instance_path, output)`。生成器不将输入配置复制进项目，也不生成 `workflow.json` 或 `.ios-workflow/project.json`。

## 生命周期

- 配置仅用于第一次生成项目。首次生成失败时可修正输入，在新的空目录重试；不要用生成器覆盖已有代码。
- 生成完成后可将输入文件归档或删除；后续开发、版本迭代、测试、发布和 review 以当前工程、源码、依赖锁、设计系统及需求为准，不读取、不核对或要求同步初始配置。
- 已有项目接入工作流只需接入 Skill 和适用规则，不要求创建生成配置。已有历史配置不参与后续门禁，也不自动删除用户文件。
- 业务约束和待办在进入开发前落实到需求及技术方案，不能仅留在一次性生成输入中；记录约束不代表生成器已实现相应功能。
- `schema_version=1`、`INSTANCE_CONFIG_KEYS` 及校验函数定义完整输入契约；字段更改只影响未来生成，不要求旧项目迁移生成配置。
- 不把凭据保存到配置，不将附件文字或配置保存视为开发、上传或发布授权。

```python
# 团队成员已经复制并修改发布包最外层示例。
result = materialize_project(project_config_path, empty_output_directory)
# 后续任务直接维护实际工程，不再读取 project_config_path。
```
