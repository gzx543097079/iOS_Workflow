# iOS AI Workflow

一套配置驱动、可迁移、可供个人与团队共用的 iOS 工程工作流。

## 能力

- 生成 Swift / Objective-C 空项目源码
- 支持 MVVM / MVC
- 支持 UIKit / SwiftUI（SwiftUI 仅支持 Swift）
- 输出 `project.yml`，通过 XcodeGen 生成 `.xcodeproj`
- 内置可版本控制、可修改的代码规范和 UI 规范
- 生成测试 TODO 和提交/review 前 Checklist
- 为 AI 编码助手提供统一的 `AGENTS.md` 上下文

## 快速开始

最简单的方式是运行交互式菜单，再用序号选择操作和项目配置：

```bash
./ios
```

如果已经知道要执行的操作，可以使用简短命令：

```bash
# 检查本机依赖
./ios doctor

# Swift + SwiftUI + MVVM
./ios new DemoApp --language swift --ui swiftui --architecture mvvm

# Swift + UIKit + MVC
./ios new LegacyStyle --language swift --ui uikit --architecture mvc

# Objective-C + UIKit + MVC
./ios new ObjCApp --language objc --ui uikit --architecture mvc
```

`./ios` 是 `./bin/iosflow` 的短入口；两种写法功能完全一致。不带参数时会进入交互模式，带参数时保持原有非交互行为，适合脚本和 CI。

生成器先创建源码与 `project.yml`。如果本机已安装 XcodeGen，会继续生成 `.xcodeproj`；否则会显示安装及后续命令。也可以使用 `--no-xcodegen` 只输出模板。

默认参数保存在 [`config/defaults.jsonc`](config/defaults.jsonc)，UI Token 保存在 [`config/design-tokens.jsonc`](config/design-tokens.jsonc)。两者使用 JSONC，可在字段后保留 `//` 注释。规则分别位于 [`standards/code-style.md`](standards/code-style.md) 和 [`standards/ui-style.md`](standards/ui-style.md)，修改并提交这些文件即可让团队共享同一套规范。

配置不固定或校验 Xcode 版本，由当前机器或 CI 选择已安装的 Xcode。Swift 语言版本、部署版本、签名、设备、本地化、测试和工程版本均可独立配置。

新项目默认预创建简体中文、繁体中文、英语、西班牙语、法语、德语、日语、韩语、巴西葡萄牙语、意大利语、阿拉伯语和俄语资源。可在 `supported_localizations` 中按目标市场增删，`default_localization` 必须包含在该列表中。

`default_language_mode` 控制 App 首次启动的语言策略：`system` 跟随设备语言，`fixed` 强制使用 `default_localization`。生成器会将两项设置写入项目的 `Info.plist` 与 `workflow.json`，供运行时语言服务读取；当前默认为 `system`，仅在显式选择 `fixed` 时使用 `default_localization`。

`comment_level` 使用 1–4 级控制生成代码的中文注释，默认值为 3。1 级不生成注释，2 级用自然语句说明页面或文件，3 级进一步说明业务方法、Model 和复杂实现思路，4 级补充属性与关键控制流。生成的注释不使用“类型职责”、“方法职责”等分类标签，不生成文件名、项目名、创建时间或 Git 信息头，也不为系统方法、代理/数据源回调或继承重写方法生成注释。

## 命令

所有命令默认在工作流仓库根目录执行。首次使用时先拉取仓库并确认 CLI 可用：

```bash
git clone git@github.com:gzx543097079/iOS_Workflow.git
cd iOS_Workflow
./ios
```

### `./ios`：交互式菜单

不带参数运行 `./ios` 后，可以从菜单选择 `new`、`checklist`、`validate`、`doctor` 或 `list-options`。选择 `new` 后，CLI 会逐项显示开发语言、UI 框架、架构、依赖管理、语言策略和注释等级等现有选项。输入序号即可选择，直接回车使用默认值。

```text
要执行的操作
  1. new (默认)
  2. checklist
  3. validate
  4. doctor
  5. list-options
  6. exit
请选择 [默认 new]:
```

如果需要查看帮助或用于 CI，继续使用非交互命令：

```bash
./ios --help
./ios validate
./ios checklist . --purpose commit
```

### `doctor`：检查本机环境

显示 Python 3、XcodeGen、`xcodebuild`、SwiftLint 和 SwiftFormat 的安装状态。XcodeGen 不存在时仍可生成源码，但不会自动生成 `.xcodeproj`。

```bash
./ios doctor
```

### `validate`：校验工作流

校验 `config/defaults.jsonc`、Design Tokens、代码/UI 规范、Checklist 模板和 `AGENTS.md`。修改工作流配置后应先执行此命令。

```bash
./ios validate
# 也可以使用 Makefile
make validate
```

校验失败时命令返回非 0 状态码，可直接用于 CI。

### `list-options`：查看可用选项

以 JSON 形式输出可选值和当前默认配置，适合在生成项目前确认团队基线。

```bash
./ios list-options
```

### `new`：生成 iOS 项目

基本格式：

```bash
./ios new <项目名> [选项]
```

不传选项时使用 `config/defaults.jsonc` 中的团队默认值。例如，在仓库同级的 `Apps` 目录生成 Swift + UIKit + MVVM 项目：

```bash
./ios new TeamApp \
  --output ../Apps \
  --language swift \
  --ui uikit \
  --architecture mvvm \
  --dependency-manager spm \
  --bundle-id-prefix com.example \
  --deployment-target 17.0 \
  --default-language-mode system \
  --comment-level 3
```

成功后会在 `../Apps/TeamApp` 中生成源码、资源、测试、`workflow.json`、`Checklist.md`、规范快照和 `project.yml`。如果本机已安装 XcodeGen，还会生成 `TeamApp.xcodeproj`。

`new` 参数：

- `--language swift|objc`：选择开发语言。
- `--ui swiftui|uikit`：选择 UI 框架；Objective-C 只支持 UIKit。
- `--architecture mvvm|mvc`：选择项目架构。
- `--navigation` / `--no-navigation`（是否生成系统导航容器，默认开启）
- `--dependency-manager pod|spm|carthage|none`（三方库引入方式，默认 `pod`）
- `--bundle-id-prefix com.example`：设置 bundle ID 前缀。
- `--bundle-id com.example.myapp`：直接指定完整 bundle ID；传入后优先于前缀。
- `--deployment-target 17.0`：设置最低 iOS 版本。
- `--objc-prefix APP`（Objective-C 类前缀，2–3 个大写字母）
- `--default-language-mode system|fixed`：跟随系统，或强制使用指定的默认语言。
- `--default-localization en`：`fixed` 模式使用的语言，必须包含在 `supported_localizations` 中。
- `--comment-level 1|2|3|4`：设置中文注释详细程度。
- `--output <目录>`：设置项目父目录，项目名会作为子目录。
- `--no-xcodegen`：只生成源码和 `project.yml`，不运行 XcodeGen。
- `--force`（仅允许覆盖空目录；不会删除已有内容）

查看 CLI 内置帮助：

```bash
./ios new --help
```

### `checklist`：执行提交或 review 前检查

提交前使用 `commit`，review 前使用 `review`：

```bash
./ios checklist ../Apps/TeamApp --purpose commit
./ios checklist ../Apps/TeamApp --purpose review
```

省略项目目录时检查当前目录，`--purpose` 默认为 `commit`：

```bash
./ios checklist
# 工作流仓库也可执行
make checklist
```

自动检查内容包括：

- `Checklist.md` 及订阅/数据打点模块是否存在。
- `workflow.json` 和工作流配置是否有效。
- 测试目录是否存在，测试中是否还有未处理的 `TODO`。
- 已暂存和未暂存 Git diff 是否包含空白错误。

如果命令返回“Checklist 未通过”，需要先处理列出的 TODO、配置或 diff 问题。自动检查通过后，仍需逐项完成 `Checklist.md` 中无法自动判定的编译、测试、订阅和打点检查。

### 退出状态

- `0`：命令成功或检查通过。
- `2`：配置、生成或 Checklist 检查失败。
- 命令行参数错误由 `argparse` 输出帮助信息并返回非 0 状态码。

## 推荐团队流程

1. 团队在此仓库维护 `config/`、`standards/` 与 `AGENTS.md`。
2. 新项目统一通过 `iosflow new` 创建。
3. 将生成测试里的 `TODO` 替换为真实业务场景。
4. 提交或 review 前完成项目的 `Checklist.md`，并运行 `iosflow checklist`；自动检查不通过时不继续。
5. 每次修改规范均走代码评审，并在规范文件的 changelog 记录原因。
6. 项目内保留生成时复制的 `Standards/`，需要跟随中央规范升级时再显式同步，避免规则静默变化。
7. CI 中执行 `./ios validate`、`./ios checklist .`、SwiftLint/SwiftFormat 和项目测试。

## 依赖策略

生成器只依赖 macOS 自带的 Python 3。`.xcodeproj` 由 [XcodeGen](https://github.com/yonaskolb/XcodeGen) 生成，避免把脆弱的 PBX 文件拼接逻辑锁死在工作流里。XcodeGen 不是生成源码的必需依赖。

`dependency_manager` 支持 `pod`（CocoaPods）、`spm`（Swift Package Manager）、`carthage`（Carthage）和 `none`。选择 `pod` 时生成 `Podfile`，选择 `carthage` 时生成 `Cartfile`；选择 `spm` 时由 Xcode/XcodeGen 在添加具体包后维护引用，选择 `none` 时不生成依赖管理文件。生成器不会自动下载或安装第三方库。
