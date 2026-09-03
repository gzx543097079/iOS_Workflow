# WorkflowDemo

用于验证 `iOS_Workflow` 的真实 iOS Demo。项目通过内部生成器创建，并在生成结果上实现本地计数、设置、运行时语言切换和关于我们功能。

## 技术栈

- Swift 5.10、UIKit、MVVM
- iOS 14.0+
- XcodeGen
- XCTest 与 XCUITest
- 无三方依赖

## 功能

- 计数增加、重置和溢出保护
- 跟随系统或在 12 种本地化语言间切换
- 语言偏好持久化并即时刷新可见页面
- 关于我们与应用版本展示

## 验证

```bash
xcodegen generate
xcodebuild -project WorkflowDemo.xcodeproj -scheme WorkflowDemo -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO build
```

需求、设计和执行证据记录在工作目录的 `iOSFlowRecords/requirements/WorkflowDemo/REQ-20260903-006.md`。
