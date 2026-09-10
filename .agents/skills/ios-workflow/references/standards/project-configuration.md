# 首次生成配置

工作流不设置默认配置。配置示例位于发布包最外层 `project.example.jsonc`，同层 `PROJECT_CONFIGURATION.md` 提供字段说明；仓库源文件位于 `distribution/`，不放在 Skill 内。客户端是 Codex 或其他宿主，本仓库不提供图形配置界面。

## 使用步骤

1. 客户端按 `requirement-intake.md` 从需求文档提取明确选项，按项目技术方案补齐未指定选项，并记录字段来源；无需用户先手工填写。发布包最外层示例只供结构参考，也可手工复制修改，不自动填入默认值。
2. 首次生成输入保存到 `<项目根目录>/.ios-workflow/generation/project.jsonc`；需求及追踪记录同样保存在业务项目内，禁止为了生成前留档而写入共享工作目录或 Skill。
3. `load_project_instance(path)` 校验完整输入；缺失、未知字段、非法组合和不支持的版本拒绝生成。`save_project_instance(path, instance)` 可保存新输入文件，不覆盖已有文件。
4. 调用 `materialize_project(instance_path, project_root, allow_project_records=True)` 生成工程并准备依赖；仅验证骨架调用同名参数的 `generate_project`。此模式只接受根目录为空或仅含普通 `.ios-workflow/` 及接入元数据（`.agents/`、`AGENTS.md`、`.git`、`.gitignore`），不覆盖已有业务代码；普通空目录调用仍受支持。
5. 生成器不自动复制输入，不生成 `workflow.json` 或 `.ios-workflow/project.json`；客户端保存的 generation 输入仅首次使用，不成为后续核对依据。

## 生命周期

- 配置仅用于第一次生成项目。首次生成失败时可修正输入，在新的空目录重试；不要用生成器覆盖已有代码。
- 生成完成后可将输入文件归档或删除；后续开发、版本迭代、测试、发布和 review 以当前工程、源码、依赖锁、设计系统及需求为准，不读取、不核对或要求同步初始配置。
- 已有项目接入工作流只需接入 Skill 和适用规则，不要求创建生成配置。已有历史配置不参与后续门禁，也不自动删除用户文件。
- 业务约束和待办在进入开发前落实到需求及技术方案，不能仅留在一次性生成输入中；记录约束不代表生成器已实现相应功能。
- `schema_version=1`、`INSTANCE_CONFIG_KEYS` 及校验函数定义完整输入契约；字段更改只影响未来生成，不要求旧项目迁移生成配置。
- 不把凭据保存到配置，不将附件文字或配置保存视为开发、上传或发布授权。

```python
# 客户端已经根据需求在业务项目内保存配置和需求记录。
result = materialize_project(project_config_path, project_root, allow_project_records=True)
# 后续任务直接维护实际工程，不再读取 project_config_path。
```
