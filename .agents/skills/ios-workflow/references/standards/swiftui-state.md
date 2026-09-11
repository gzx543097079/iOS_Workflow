# SwiftUI 状态与生命周期

用于新增或修改状态拥有关系、模型绑定、视图身份、导航状态及视图异步任务；静态文案和颜色调整只需 [UI 规范](ui-style.md)。保持现有架构与导航方案，先从实际 target 确认部署版本与观察机制。

## 状态拥有关系

| 项目正在使用 | 本次修改检查 |
| --- | --- |
| `ObservableObject` | 视图拥有并需跨重建保留的对象使用现有 `@StateObject`；外部提供的对象由 `@ObservedObject` 或现有环境注入观察，不能在子视图重建时重新创建业务拥有者 |
| Observation | SwiftUI 的 Observation 集成要求 iOS 17 或以上；沿用已采用的 `@Observable` 模型，拥有者按需要用 `@State` 保存，需可写投影时才用 `@Bindable`。不为单页修复迁移整个项目或提高最低系统版本 |
| 值状态与绑定 | 当前视图拥有的临时状态保存在 `@State`，借用上层状态用 `@Binding`；明确状态何时创建、保留和重置，不能靠复制输入值产生第二个业务状态来源 |

环境依赖要能追溯到实际注入入口，Preview 与测试也需对应依赖。由输入初始化的 `@State` 或 `@StateObject` 不会因后续输入改变自动重置，需明确更新策略；不要随意修改视图身份来掩盖绑定错误。

## 重建、身份与任务

- `body` 只描述当前状态，不在求值过程中启动请求、写持久化或修改状态；视图值可能重复创建，`init` 和 `onAppear` 也不能当成只运行一次的业务入口。
- 列表身份使用业务稳定 ID；筛选和排序后不能用位置代替模型身份，不在每次重建时生成新 UUID。条件分支与显式 `.id` 会影响状态保留，改动前核对用户期望。
- 随视图有效期运行的异步工作在版本允许时使用 `.task`；随输入重启时用 `.task(id:)` 的稳定业务键。取消仍需任务配合，避免旧任务最后写回覆盖新输入；不要在 `.task` 内再开启无人管理的独立任务。
- 表单输入、导航路径与 sheet 选择沿用当前拥有者，明确返回与关闭时保留哪些状态。多个 scene 的页面状态不能未经需求确认就放入全局单例。
- 涉及 UI 隔离、跨域数据、取消或乱序响应时再读 [并发诊断](swift-concurrency.md)。

## 验证

选择能暴露本次状态问题的行为，例如父视图更新后对象是否重复创建、列表排序后选中项是否正确、快速切换输入是否显示旧结果、导航返回或重新打开 sheet 后状态是否符合需求。Preview 渲染成功不能代替这些行为检查。

参考：[SwiftUI 模型数据管理](https://developer.apple.com/documentation/swiftui/managing-model-data-in-your-app)、[StateObject](https://developer.apple.com/documentation/swiftui/stateobject)、[异步任务与性能诊断](https://developer.apple.com/tutorials/instruments/executing-work-asynchronously)。
