# 配置示例

首次生成项目时，复制同层 `project.example.jsonc` 后按项目需求修改。它不是默认配置，生成器不会自动加载它，也不会补全缺失字段。

| 字段 | 接入时填写 |
| --- | --- |
| `project_name` | 工程名称 |
| `config.language` / `ui` | `swift` 或 `objc`；`swiftui` 或 `uikit`，Objective-C 不支持 SwiftUI |
| `config.architecture` | `mvvm` 或 `mvc` |
| `config.dependency_manager` | `pod`、`spm`、`carthage` 或 `none` |
| `config.bundle_id` / `bundle_id_prefix` | 完整 Bundle ID；完整值为空时项目明确选择由前缀与名称组合 |
| `config.deployment_target` / `swift_version` | 最低 iOS 版本、Swift 语言版本 |
| `config.marketing_version` / `build_number` | 产品版本和构建号 |
| `config.target_devices` | `iphone`、`ipad` 的非空数组 |
| `config.supported_orientations` | `portrait`、`portrait_upside_down`、`landscape_left`、`landscape_right`；空数组表示选择平台方向行为 |
| `config.supported_localizations` / `default_localization` | 支持的语言与默认本地化语言，后者必须包含在前者中 |
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

完整接入与生成方式见 `.agents/skills/ios-workflow/references/standards/project-configuration.md`（发布包内）。示例内的语言、配色、组织名和工具选择都不代表对业务项目的要求。

配置仅首次生成使用。生成完成后无需保留在项目中，后续开发、测试和发布不读取、不核对或同步它。
