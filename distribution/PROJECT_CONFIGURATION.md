# 配置示例

首次生成项目时，客户端根据需求文档与明确的项目选型，以同层 `project.example.jsonc` 为结构参考生成完整输入；团队也可以手工复制修改。它不是默认配置，生成器不会自动加载它，也不会补全缺失字段。

| 字段 | 接入时填写 |
| --- | --- |
| `project_name` | 工程名称 |
| `config.language` / `ui` | `swift` 或 `objc`；`swiftui` 或 `uikit`，Objective-C 不支持 SwiftUI |
| `config.architecture` | `mvvm` 或 `mvc` |
| `config.dependency_manager` | `pod`、`spm`、`carthage` 或 `none` |
| `config.bundle_id` / `bundle_id_prefix` | 完整 Bundle ID；完整值为空时项目明确选择由前缀与名称组合 |
| `config.deployment_target` | 项目明确的最低 iOS 版本；当前 UIKit 骨架要求至少 `13.0`，SwiftUI 骨架至少 `14.0`，不自动补值或提高项目要求 |
| `config.swift_version` | 生成器支持的 Swift 语言模式：字符串 `5` 或 `6`，写入 `SWIFT_VERSION`；`5.10` 是工具链版本，不是合法语言模式 |
| `config.marketing_version` / `build_number` | 产品版本和构建号 |
| `config.target_devices` | `iphone`、`ipad` 的非空数组 |
| `config.supported_orientations` | `portrait`、`portrait_upside_down`、`landscape_left`、`landscape_right`；空数组表示选择平台方向行为 |
| `config.supported_localizations` / `default_localization` | `en`、`zh-Hans` 等连字符语言标识，不允许路径或大小写重复；默认语言必须包含在支持列表中 |
| `config.default_language_mode` | `system` 跟随系统或 `fixed` 固定读取默认本地化语言 |
| `config.localization_strings` | 每个文案键提供全部支持语言的译文 |
| `config.supports_dark_mode` / `supports_manual_dark_mode_switch` | 深色适配与手动外观策略；不支持深色时不能启用手动切换 |
| `config.include_unit_tests` / `include_ui_tests` | 测试 target 开关；当前 `test_framework` 支持 `xctest` |
| `config.development_team` / `code_sign_style` | 项目的 Team ID 与 `automatic` 或 `manual` 签名；不要填写私钥 |
| `config.comment_level` | 1–4，详见代码生成规范 |
| `config.strict_concurrency` | `minimal`、`targeted` 或 `complete` |
| `design_tokens` | 项目的尺寸、字体、颜色和动效；当前颜色值使用 UIKit 系统色成员名 |
| `sources` / `constraints` | 字段来源与业务约束；示例标记应改成项目的实际决定 |

其余布尔字段按项目是否需要导航、警告视为错误、隐私清单、Xcode 工程生成等能力填写。所有字段都应保留，不能以删除字段表示禁用。

Xcode/Swift 编译工具链版本在实际构建证据的环境中记录，须支持所选语言模式。此字段修正只作用于首次生成输入，不读取或迁移已有项目的历史生成配置。

完整接入与生成方式见 `.agents/skills/ios-workflow/references/standards/project-configuration.md`（发布包内）。示例内的语言、配色、组织名和工具选择都不代表对业务项目的要求。

配置仅首次生成使用。生成完成后无需保留在项目中，后续开发、测试和发布不读取、不核对或同步它。

文档导入的输入保存到业务项目 `.ios-workflow/generation/`。执行记录和日志同样属于该项目，禁止保存在 Skill 或公共工作流目录。生成器的 `allow_project_records=True` 模式只允许目标已有 `.ios-workflow/` 和普通 Git/Skill 接入元数据。
