# WorkflowDemo

用于验证 `iOS_Workflow` 的真实 iOS Demo。项目通过内部生成器创建，并在生成结果上实现本地计数、设置、运行时语言切换和关于我们功能。

## 技术栈

- Swift 5.10、UIKit、MVVM
- iOS 14.0+
- XcodeGen
- XCTest 与 XCUITest
- 无三方依赖

## 功能

- 商城风格首页：本地商品搜索、数码／生活分类、商品卡片与详情弹窗
- 商城使用示例商品和价格，支持现有 12 种语言；不提供真实下单或支付

- 计数增加、重置和溢出保护
- 跟随系统或在 12 种本地化语言间切换
- 语言偏好持久化并即时刷新可见页面
- 关于我们与应用版本展示

## 验证

```bash
xcodegen generate
xcodebuild -project WorkflowDemo.xcodeproj -scheme WorkflowDemo -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO build
```

需求、进度和交接记录位于本项目 `.ios-workflow/`。新对话先读取 `.ios-workflow/handoff.md`，再按需求 ID 读取档案和验收账本。本次商城需求为事后补录；原 Demo 历史已保留，不能把历史通过结果直接当作当前验收。
