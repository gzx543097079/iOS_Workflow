# Swift 并发诊断

用于修改异步任务、actor 隔离、跨域数据传递，或定位并发诊断、取消失效及异步结果覆盖问题。普通同步代码修改不加载本模块。

## 先确认实际语义

- 从受影响 target 的实际构建设置或 `Package.swift` 确认 Swift 语言模式、严格并发检查、默认 actor 隔离和已启用的相关特性；需要时用当前 scheme/configuration 的 `xcodebuild -showBuildSettings` 核对有效值。工具链版本、`swift-tools-version` 和语言模式不是同一信息，不回读首次生成配置。
- 保留原始诊断、具体符号、调用方与数据拥有者，画清本次涉及的隔离边界即可。设置仍不明时先查工程与编译输出；不要通过猜测新版本默认值实施迁移。
- 延续项目已有 async/await、回调、Combine 或队列方案。仅当当前需求需要时调整边界；新语法先核对实际工具链、SDK 与部署版本支持。

## 按症状选择最小修复

| 症状 | 检查与处理 |
| --- | --- |
| UI 状态隔离报错 | 确认状态是否确实由 UI 拥有，再隔离对应类型、成员或调用；不要给整个模块统一加 `@MainActor` |
| 非 Sendable 数据跨边界 | 找出并发访问同一可变对象的位置，优先限定拥有者或传递值快照；`@unchecked Sendable`、`@preconcurrency`、`nonisolated(unsafe)` 需解释本处安全依据，不能只为消除诊断 |
| 卡顿或任务执行位置不符 | `async`、`await` 或 `Task {}` 本身不保证后台执行；检查耗时同步段的实际隔离，再按项目支持能力移出 UI 执行路径，不默认使用 `Task.detached` |
| 取消后仍更新、旧请求覆盖新结果 | 明确谁持有任务、何时取消以及取消如何传播；取消是协作式的，写回前核对取消状态及请求身份。错误处理不能把取消显示成业务失败 |
| actor 内逻辑竞态 | `await` 后先复核之前依赖的可变状态；隔离防止数据竞争，不保证跨挂起点的业务前提仍成立 |
| 回调桥接为 async | 成功、失败、取消竞争时 continuation 只能恢复一次；核对底层操作是否支持取消，不用信号量把异步操作同步阻塞 |

优先保留结构化任务关系。确需独立任务时说明拥有者、结束条件和错误出口；页面退出是否取消由业务生命周期决定，不能一律取消或一律保留。

## 验证

先重编译受影响 target 确认原诊断已解决，再选择与改动相关的测试，例如交错响应、取消、重复调用或状态在挂起期间变化。性能改善需实测；编译成功不证明无逻辑竞态，也不要求无关模块迁移。

参考：[Swift 并发语言指南](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/)、[Swift 并发诊断 Skill](https://github.com/AvdLee/Swift-Concurrency-Agent-Skill/blob/main/skills/swift-concurrency/SKILL.md)。这里只借鉴诊断顺序，具体语法以本项目工具链为准。
