# iOS 核心代码规范

## 基线

- 默认遵循 Swift API Design Guidelines、Apple Human Interface Guidelines 和项目现有约定。
- 使用 4 空格缩进、UTF-8、LF，并保留文件末尾换行；新增警告必须处理，不无说明地屏蔽。
- 优先使用项目已经采用的语言、UI 框架、架构与依赖方案。
- 不因个人偏好引入第二套架构、状态管理或基础设施。
- 新增业务模块保持 `Features/<Feature>` 边界；跨模块能力放入项目既有共享层。

## 命名

- 类型使用 `UpperCamelCase`，方法、属性、局部变量和参数使用 `lowerCamelCase`。
- Bool 名称表达判断含义，如 `isLoading`、`hasPermission`、`canSubmit`。
- 缩写视为普通单词，除非是 Apple 平台惯例：优先 `userId`、`urlString`，保留 `URL`、`HTTP`、`JSON` 等系统通用写法。
- 名称表达业务含义，避免无上下文的 `data`、`info`、`manager`、`handler`。
- 文件名通常与主类型一致；扩展文件使用 `Type+Purpose.swift`。
- 协议名称表达能力或角色，例如 `ImageLoading`、`SessionProviding`。
- Apple 平台、框架和源码标识符使用官方大小写；AI、API、CI、HTTP、ID、JSON、RTL、SDK、UI、URL 等技术缩写保持大写，普通英文名词在句中使用小写。

## Swift

- 默认使用 `struct` 表达值语义；确需引用语义、继承或 Objective-C 互操作时使用 `class`。
- class 无继承需求时标记 `final`。
- 优先 `let`，只在确需修改时使用 `var`。
- 避免强制解包、强制类型转换和隐式解包；若平台约束保证安全，应让理由在上下文中清晰可见。
- 使用 `guard` 提前退出，减少嵌套；异步逻辑优先采用项目已有的 async/await 或响应式方案。
- UI 状态只在主线程或 `@MainActor` 上更新。
- 控制类型和方法规模；拆分依据是职责与可测试边界，而不是机械行数。
- 访问级别从最小范围开始，除非 API 明确需要扩大可见性。

## Objective-C

- 类名遵循项目现有前缀策略；方法和属性使用 lower camel case。
- 使用轻量泛型和 nullability；公开头文件保持最小化。
- 使用属性语义准确表达所有权，Block 属性通常使用 `copy`，delegate 通常使用 `weak`。
- 新异步 API 明确回调线程和错误语义。
- 避免新增宏式常量；优先 `static const` 或类型安全封装。
- 新旧代码交互时保持现有桥接边界，不无理由扩大 Objective-C 暴露面。

## 架构与数据流

- View 负责展示和用户事件转发，不直接承担网络、持久化或复杂业务编排。
- Model 表达领域数据；ViewModel、Presenter 或 Controller 遵循项目既有架构承担状态转换和协调。
- 依赖从外部注入；避免业务代码直接依赖全局单例，除非项目已明确采用该模式。
- 公共 API 保持小而稳定；跨模块访问通过明确接口完成。
- 并发任务需要考虑取消、重复请求、生命周期和错误恢复。

## 错误、日志与隐私

- 错误使用有业务含义的类型，不以字符串判断分支；不静默吞掉错误。
- 日志不得包含访问令牌、密码、完整支付信息或其他敏感数据。
- 用户可见错误使用可本地化文案，不直接展示内部错误描述。
- 生产环境使用项目日志设施或 `Logger`，不遗留 `print`；权限只在功能需要时请求并说明用途。
- 涉及权限、订阅、支付、账户和埋点时，保持数据采集最小化并遵守项目隐私约定。

## 测试与交付

- 修改后运行最小相关测试；生成器变更必须运行仓库规定的完整生成器测试。
- 新业务逻辑优先覆盖正常路径、关键边界和错误路径；缺陷修复应复现问题或增加回归测试。
- 测试名表达条件和结果，例如 `test_load_whenRequestFails_showsRetryState`。
- 提交只包含当前任务相关变更，不覆盖用户已有的无关修改。
- 提交、推送或 review 时按 `checklists/pre-commit-review.md` 执行门禁。
