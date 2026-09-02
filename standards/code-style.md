# iOS 代码规范 v1.5

## 基线

- Swift 遵循 Swift API Design Guidelines；Objective-C 遵循 Apple Cocoa Coding Guidelines。
- 编译器警告视为需要处理的问题，不用无说明的方式屏蔽。
- 单文件聚焦一个主要类型；文件名与主要类型一致。
- 使用 4 空格缩进，UTF-8，LF，文件末尾保留换行。
- 优先系统 SDK 与少量、可审计的依赖；引入依赖需说明收益、体积、许可与替代方案。

## 命名

- 类型使用 `UpperCamelCase`，属性、方法和局部变量使用 `lowerCamelCase`。
- 布尔值使用可读前缀，如 `isLoading`、`hasPermission`、`canRetry`。
- 避免 `Manager`、`Helper`、`Util` 等宽泛命名，名称应体现职责。
- 协议优先表达能力或角色，例如 `ImageLoading`、`SessionProviding`。
- Objective-C 类必须使用项目指定的 2–3 字母前缀；分类采用 `ClassName+Purpose`。

## 英文与技术名词大小写

- 产品、平台、语言和框架名称遵循官方写法，例如 iOS、macOS、Xcode、Swift、Objective-C、SwiftUI、UIKit、Combine 和 Foundation。
- 技术缩写保持大写，例如 AI、API、CI、HTTP、ID、JSON、RTL、SDK、UI 和 URL。
- 普通英文名词在句中使用小写，例如 app、block、build、delegate、feature、lint、nullability、token 和 unit test。
- API 类型、协议、属性、方法和枚举值保持源码中的准确大小写，并使用代码格式标记，例如 `UIViewController`、`ObservableObject`、`systemBackground` 和 `isLoading`。
- 标题或句首之外，不因强调而把普通英文名词首字母大写。

## Swift

- 默认使用 `struct`；需要身份、继承或共享可变状态时才使用 `class`。
- 类若不用于继承则标记 `final`。
- 不使用 `!` 强制解包，除非生命周期可由框架严格证明，并附简短说明。
- 优先 `async/await`；UI 状态更新置于 `@MainActor`。
- 使用明确的访问控制，默认从 `private` 开始逐步放宽。
- `View`/`UIViewController` 不直接访问网络或持久化层。

## Objective-C

- 启用 nullability，并使用轻量泛型。
- 属性明确 `strong`、`copy`、`weak` 与 `assign` 语义。
- block 属性使用 `copy`；delegate 通常使用 `weak`。
- 公共头文件只暴露必要 API，私有声明放在 class extension。
- 新异步 API 明确回调线程与错误语义。

## 生成代码注释

`comment_level` 只控制新生成的手写代码，不要求在生成完成后扫描或批量补写已有代码：

1. 不生成解释性注释。
2. 使用中文自然语句说明页面或文件的用途。
3. 在第 2 级基础上，说明每个业务自定义方法的作用、Model 的用途，以及难度较高实现的关键思路。
4. 在第 3 级基础上，为重要属性、关键控制流、边界条件和错误处理补充尽可能完整且有价值的说明。

所有等级均遵守以下限制：

- 不为系统方法、继承重写方法、生命周期方法及代理或数据源回调生成注释。
- 不生成文件名、项目名、创建时间、作者、Git 分支或 commit 等文件头信息。
- 不使用“类型职责”“方法职责”“Model 职责”等分类标签，注释直接使用自然语言。
- 不复述代码表面行为，注释应解释业务目的、约束或不直观的实现原因。

## 三方库引入方式

`dependency_manager` 决定新项目和新增三方库使用的唯一依赖管理方式：

- `pod`：新项目生成 `Podfile`；新增库只写入 `Podfile`，不同时添加 Swift Package 或 Carthage 配置。
- `spm`：通过 Xcode 工程或 `project.yml` 的 Swift Package 引用管理依赖，不生成 `Podfile` 或 `Cartfile`。
- `carthage`：新项目生成 `Cartfile`；新增库只写入 `Cartfile`。
- `none`：不预设依赖管理文件；确需引入三方库时先向用户确认新的依赖管理方式。

选择依赖管理方式不代表可以虚构业务不需要的三方库。没有指定具体依赖时，`Podfile` 或 `Cartfile` 可以只保留有效的项目结构和添加说明。

### 版本约束

- 所有直接三方库必须明确指定完整、精确的发布版本号，例如 `1.2.3`。
- CocoaPods 使用 `pod 'LibraryName', '1.2.3'`，禁止 `>`, `>=`, `<`, `<=`, `~>`、通配符及省略版本。
- Swift Package Manager 使用 `.exact("1.2.3")` 或 Xcode 中的 Exact Version，禁止 `from`、版本范围、`upToNextMajor`、`upToNextMinor`、branch、revision 及未指定版本。
- Carthage 使用 `github "Owner/Library" == 1.2.3`，禁止 `>=`、`~>`、分支、commit 及省略版本。
- 禁止使用 `latest`、“最新稳定版”、“高于”、“低于”、“至少”、“兼容某版本”等浮动表达；必须先解析成用户确认或项目明确指定的具体版本号。
- `Podfile.lock`、`Package.resolved` 和 `Cartfile.resolved` 等解析结果文件应随项目提交，确保直接和传递依赖可复现。

### 安装、更新与编译

依赖操作必须在业务项目目录执行。命令不可用、依赖解析失败或安装失败时，停止后续编译并向用户报告。

#### CocoaPods

- 新建项目或新增依赖后运行 `pod install`，并使用生成的 `.xcworkspace` 编译。
- 明确修改某个 pod 的精确版本后，运行 `pod update POD_NAME`，不得无目标地更新全部 pods。
- 每次编译前运行 `pod install`，确认本地安装结果与 `Podfile`、`Podfile.lock` 一致，再使用 `.xcworkspace` 执行构建。

#### Swift Package Manager

- 新建项目、增加依赖或修改精确版本后，运行包解析操作并更新 `Package.resolved`；Xcode 项目使用 `xcodebuild -resolvePackageDependencies`。
- 每次编译前先执行依赖解析，确认已取得精确版本，再执行构建。
- 不得通过自动切换到分支、revision 或版本范围解决解析冲突；应向用户报告冲突并确认具体版本。

#### Carthage

- 新建项目或修改依赖的精确版本后，运行 `carthage update DEPENDENCY_NAME --use-xcframeworks` 并更新 `Cartfile.resolved`；首次解析多个已明确版本的依赖时可统一执行 `carthage update --use-xcframeworks`。
- 每次编译前运行 `carthage bootstrap --use-xcframeworks`，按 `Cartfile.resolved` 安装并构建依赖。
- 不得手工编辑 `Cartfile.resolved`。

#### None

- `dependency_manager` 为 `none` 时不运行依赖安装或更新命令。
- 项目出现三方库需求后，先让用户明确选择依赖管理方式和精确版本，再生成配置并执行对应操作。

## 架构边界

- `Features` 按业务能力分组，不按纯技术类型堆成全局目录。
- MVVM：View 只渲染与转发事件；ViewModel 管理展示状态和用户意图；Model/Service 处理领域与数据。
- MVC：Controller 负责协调，不承载网络、存储与复杂领域计算；复杂逻辑下沉到 Model/Service。
- 跨 feature 复用代码进入 `Core` 或 `DesignSystem` 前，至少有两个真实使用方。
- 通过协议注入外部依赖，使业务逻辑可测试。

## 错误、日志与隐私

- 错误使用有含义的类型，不用字符串判断分支。
- 用户提示与诊断信息分离；日志不得包含 token、密码或个人敏感数据。
- 生产环境使用 `Logger`，不要遗留 `print`。
- 权限请求只在功能需要时触发，并提供清楚的用途说明。

## 测试与提交

- ViewModel、Controller 中的业务分支及错误恢复必须有单元测试。
- bug 修复应先复现或增加回归测试。
- 测试命名表达条件与结果，例如 `test_load_whenRequestFails_showsRetryState`。
- 提交保持单一意图；格式化、重构与行为修改尽量分开。

## 工具建议

- SwiftFormat 负责机械格式化，SwiftLint 负责可配置的静态规则。
- CI 至少执行 lint、build 和 unit tests。
- 工具配置是本规范的机器可执行补充；冲突时以本文件明确条款为准。

## Changelog

- 1.5：要求三方库使用精确版本，并在新建、版本更新和编译阶段执行对应的安装、更新或解析操作。
- 1.4：明确生成阶段的四级中文注释规则和三方库引入方式，不增加生成后的强制核对。
- 1.3：提交或推送前自动执行 Checklist，并使用统一状态标记和失败门禁。
- 1.2：移除对工作流 CLI 和生成器校验的依赖，保留项目自身的构建与测试要求。
- 1.1：统一官方名称、技术缩写、普通英文名词和代码标识符的大小写规则。
- 1.0：建立 Swift/Objective-C、MVVM/MVC、并发、测试与隐私基线。
