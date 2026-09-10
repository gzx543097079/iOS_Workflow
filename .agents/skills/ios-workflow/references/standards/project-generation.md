# iOS 项目生成规范

仅在新建项目或修改项目生成器时读取。本模块是 Codex 可导入的内部工具，不提供团队成员需要记忆的 CLI 命令。

## 生成顺序

1. 先按 `project-configuration.md` 保存需求对应的项目实例，再向 `scripts/project_generation.py` 传入 `instance_path`；生成器通过 `load_project_instance` 读取并校验实例，调用方不把完整配置输出到模型上下文；字段、版本、Bundle ID、本地化或技术组合非法时，在写入项目文件前停止。
2. 默认目标目录必须不存在或为空；`allow_project_records=True` 允许目录仅含普通 `.ios-workflow/` 及接入元数据（`.agents/`、`AGENTS.md`、`.git`、`.gitignore`），以容纳文档和首次生成输入。两种模式都不覆盖已有业务代码，不允许记录目录通过符号链接写到项目外。项目名转换为合法标识符，产品模块名与系统框架隔离。
3. 按语言、UI、架构、导航、外观、本地化策略、测试、签名和设备配置生成源码与 `project.yml`。
4. 生成 Swift 或 Objective-C DesignTokens；注释只在生成阶段按 `comment_level` 写入。
5. 通过 XcodeGen 生成唯一 `.xcodeproj`，不手工拼接 `project.pbxproj`。工具缺失或生成失败时停止并保留已生成文件供排查。
6. 按 `references/standards/dependencies.md` 准备依赖；之后才允许编译。任何依赖失败都不得伪装为项目生成成功。

## 支持范围

- 支持 Swift + UIKit、Swift + SwiftUI、Objective-C + UIKit；Objective-C + SwiftUI 必须提前拒绝。
- `swift_version` 表示语言模式，当前骨架支持字符串 `5` 或 `6`，直接写入 `SWIFT_VERSION`；不得传入 `5.10` 等工具链版本。编译前确认实际 Xcode/Swift 支持所选模式，并在验证环境中记录工具链版本。
- `system` 跟随系统本地化；`fixed` 从 `default_localization` 对应资源读取，资源缺失时安全回退系统语言。
- `localization_strings` 中每个用户可见文案键必须覆盖 `supported_localizations` 的全部语言；生成器按配置写入对应 `.lproj/Localizable.strings`，缺少译文时在写文件前拒绝生成。
- 本地化标识使用 `en`、`zh-Hans`、`pt-BR` 等连字符形式，拒绝路径和大小写重复项。生成前检查全部输出路径；写入以项目目录为边界，拒绝符号链接重定向并只创建新文件，遇到并发产生的已有文件也不覆盖。
- UIKit 与 SwiftUI 生成结果必须兼容 `deployment_target`，不可使用高于最低版本且无降级路径的 API。
- MVVM 生成最小 ViewModel，MVC 不生成 ViewModel；`navigation_enabled` 必须真实决定根导航容器。
- `supports_dark_mode` 为 `false` 时在工程配置中固定浅色外观；`supports_manual_dark_mode_switch` 为 `true` 时生成持久化的跟随系统、浅色和深色切换策略，但不自动生成设置页面。手动切换不能在暗黑模式关闭时启用。
- 按配置生成单元测试、UI 测试、本地化资源和隐私清单；测试骨架保留明确 TODO。

## 输出与验证

- `scripts/project_generation.py` 返回生成文件列表和工程、依赖准备摘要，调用方据此向用户说明实际生成了哪些文件及用途。
- 生成器变更至少覆盖配置错误、三种技术组合、注释等级、语言模式、多语言文案覆盖、架构、导航、外观和测试开关。
- 本机具备 XcodeGen/Xcode 时，三种支持组合都应生成工程；影响源码模板或工程设置时执行无签名模拟器编译。
