# iOS 代码规范 v1.1

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
- CI 至少执行生成器校验、lint、build 和 unit tests。
- 工具配置是本规范的机器可执行补充；冲突时以本文件明确条款为准。

## Changelog

- 1.1：统一官方名称、技术缩写、普通英文名词和代码标识符的大小写规则。
- 1.0：建立 Swift/Objective-C、MVVM/MVC、并发、测试与隐私基线。
