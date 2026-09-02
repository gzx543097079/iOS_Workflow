# iOS AI Workflow

一套配置驱动、可迁移、可供个人与团队共用的 iOS 工程工作流。

## 能力

- 生成 Swift / Objective-C 空项目源码
- 支持 MVVM / MVC
- 支持 UIKit / SwiftUI（SwiftUI 仅支持 Swift）
- 输出 `project.yml`，通过 XcodeGen 生成 `.xcodeproj`
- 内置可版本控制、可修改的代码规范和 UI 规范
- 为 AI 编码助手提供统一的 `AGENTS.md` 上下文

## 快速开始

```bash
# 检查本机依赖
./bin/iosflow doctor

# Swift + SwiftUI + MVVM
./bin/iosflow new DemoApp --language swift --ui swiftui --architecture mvvm

# Swift + UIKit + MVC
./bin/iosflow new LegacyStyle --language swift --ui uikit --architecture mvc

# Objective-C + UIKit + MVC
./bin/iosflow new ObjCApp --language objc --ui uikit --architecture mvc
```

生成器先创建源码与 `project.yml`。如果本机已安装 XcodeGen，会继续生成 `.xcodeproj`；否则会显示安装及后续命令。也可以使用 `--no-xcodegen` 只输出模板。

默认参数保存在 [`config/defaults.jsonc`](config/defaults.jsonc)，UI Token 保存在 [`config/design-tokens.jsonc`](config/design-tokens.jsonc)。两者使用 JSONC，可在字段后保留 `//` 注释。规则分别位于 [`standards/code-style.md`](standards/code-style.md) 和 [`standards/ui-style.md`](standards/ui-style.md)，修改并提交这些文件即可让团队共享同一套规范。

配置不固定或校验 Xcode 版本，由当前机器或 CI 选择已安装的 Xcode。Swift 语言版本、部署版本、签名、设备、本地化、测试和工程版本均可独立配置。

新项目默认预创建简体中文、繁体中文、英语、西班牙语、法语、德语、日语、韩语、巴西葡萄牙语、意大利语、阿拉伯语和俄语资源。可在 `supported_localizations` 中按目标市场增删，`default_localization` 必须包含在该列表中。

## 命令

```bash
./bin/iosflow new <项目名> [选项]
./bin/iosflow validate
./bin/iosflow doctor
./bin/iosflow list-options
```

`new` 支持：

- `--language swift|objc`
- `--ui swiftui|uikit`
- `--architecture mvvm|mvc`
- `--navigation` / `--no-navigation`（是否生成系统导航容器，默认开启）
- `--dependency-manager pod|spm|carthage|none`（三方库引入方式，默认 `pod`）
- `--bundle-id-prefix com.example`
- `--bundle-id com.example.myapp`
- `--deployment-target 17.0`
- `--objc-prefix APP`（Objective-C 类前缀，2–3 个大写字母）
- `--output <目录>`
- `--no-xcodegen`
- `--force`（仅允许覆盖空目录；不会删除已有内容）

## 推荐团队流程

1. 团队在此仓库维护 `config/`、`standards/` 与 `AGENTS.md`。
2. 新项目统一通过 `iosflow new` 创建。
3. 每次修改规范均走代码评审，并在规范文件的 changelog 记录原因。
4. 项目内保留生成时复制的 `Standards/`，需要跟随中央规范升级时再显式同步，避免规则静默变化。
5. CI 中执行 `./bin/iosflow validate`、SwiftLint/SwiftFormat 和项目测试。

## 依赖策略

生成器只依赖 macOS 自带的 Python 3。`.xcodeproj` 由 [XcodeGen](https://github.com/yonaskolb/XcodeGen) 生成，避免把脆弱的 PBX 文件拼接逻辑锁死在工作流里。XcodeGen 不是生成源码的必需依赖。

`dependency_manager` 支持 `pod`（CocoaPods）、`spm`（Swift Package Manager）、`carthage`（Carthage）和 `none`。选择 `pod` 时生成 `Podfile`，选择 `carthage` 时生成 `Cartfile`；选择 `spm` 时由 Xcode/XcodeGen 在添加具体包后维护引用，选择 `none` 时不生成依赖管理文件。生成器不会自动下载或安装第三方库。
