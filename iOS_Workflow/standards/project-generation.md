# iOS 项目生成规范

仅在新建项目或修改项目生成器时读取。本模块是 Codex 可导入的内部工具，不提供团队成员需要记忆的 CLI 命令。

## 生成顺序

1. 由 `tools/project_generation.py` 直接读取并校验 `config/defaults.jsonc` 和 `config/design-tokens.jsonc`，调用方不把完整配置输出到模型上下文；字段、版本、Bundle ID、本地化或技术组合非法时，在写入项目文件前停止。
2. 目标目录必须不存在或为空，不覆盖已有项目。项目名转换为合法标识符，产品模块名与系统框架隔离。
3. 按语言、UI、架构、导航、本地化策略、测试、签名和设备配置生成源码与 `project.yml`。
4. 生成 Swift 或 Objective-C DesignTokens；注释只在生成阶段按 `comment_level` 写入。
5. 通过 XcodeGen 生成唯一 `.xcodeproj`，不手工拼接 `project.pbxproj`。工具缺失或生成失败时停止并保留已生成文件供排查。
6. 按 `standards/dependencies.md` 准备依赖；之后才允许编译。任何依赖失败都不得伪装为项目生成成功。

## 支持范围

- 支持 Swift + UIKit、Swift + SwiftUI、Objective-C + UIKit；Objective-C + SwiftUI 必须提前拒绝。
- `system` 跟随系统本地化；`fixed` 从 `default_localization` 对应资源读取，资源缺失时安全回退系统语言。
- UIKit 与 SwiftUI 生成结果必须兼容 `deployment_target`，不可使用高于最低版本且无降级路径的 API。
- MVVM 生成最小 ViewModel，MVC 不生成 ViewModel；`navigation_enabled` 必须真实决定根导航容器。
- 按配置生成单元测试、UI 测试、本地化资源和隐私清单；测试骨架保留明确 TODO。

## 输出与验证

- `tools/project_generation.py` 返回生成文件列表和工程、依赖准备摘要，调用方据此向用户说明实际生成了哪些文件及用途。
- 生成器变更至少覆盖配置错误、三种技术组合、注释等级、语言模式、架构、导航和测试开关。
- 本机具备 XcodeGen/Xcode 时，三种支持组合都应生成工程；影响源码模板或工程设置时执行无签名模拟器编译。
- 工程生成后端的长期选择见 `docs/adr/0001-use-xcodegen-for-project-generation.md`。
