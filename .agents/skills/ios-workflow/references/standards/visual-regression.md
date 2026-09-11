# 关键页面视觉回归（可选）

仅在 UI 验收需要发现布局、截断或外观回归时加载。先选择少量关联验收的页面和状态，沿用项目现有截图工具；不向生成器、App target 或所有项目默认加入测试依赖。图像比较不能替代交互、VoiceOver、业务断言或人工首次审阅。

## 固定输入与采集

1. 将[环境示例](../../assets/templates/testing/visual-context.example.json)复制到 `<项目根目录>/.ios-workflow/tests/visual/<场景>/context.json`，根据实际捕获环境填写。记录 Xcode 版本与 build、模拟器系统与 build、设备、视口点数、scale、语言、外观、字体级别、方向、关联验收与夹具版本。示例值没有默认效力，也不属于首次生成配置；`unknown`、`TBD`、`未知`、`待补充` 等未知值与示例占位符不能作为录制或比较证据，大小写和首尾空白不会绕过检查。
2. 固定数据、时钟、网络结果、动画终态和加载状态。优先捕获目标 view；全屏截图还须固定状态栏。改变外观、语言或字体是独立场景，不相互覆盖基线。
3. 可把[原生 XCTest 采集模板](../../assets/templates/testing/VisualCaptureTests.swift)复制到已有 UI-test target，替换就绪标记和数据准备，等待可观察终态后保留附件。SwiftUI 页面也可用此 UI-test 方式；Objective-C 项目可使用已有截图测试，不要求改变 App 语言。
4. 例如 `xcrun simctl ui <实际设备UDID> appearance light` 固定外观；按实际需要用 `simctl status_bar` 固定状态栏并在结束时恢复设置。`xcodebuild test` 明确 destination，保存 `.xcresult`。用 `xcrun xcresulttool export attachments --path <结果.xcresult> --output-path <项目artifacts中的新目录> --test-id <实际测试标识>` 导出附件，从其 `manifest.json` 定位命名截图，不能选取错误页面或测试运行。版本差异先查当前工具的 `--help`。

## 审阅基线与比较

发布包包含[原生比较助手](../../scripts/visual_snapshot.swift)，只需 macOS 的 Swift、AppKit 和 CryptoKit，无第三方库。先查看截图并核对需求；客户端保存实际审阅者和审阅记录引用，不能让模型凭“生成成功”捏造同意。以下命令中的路径均替换为业务项目路径，`--baseline` 和 `--output` 必须为尚不存在的新目录：

```sh
swift <Skill目录>/scripts/visual_snapshot.swift record \
  --image <候选截图.png> --context <当前环境.json> \
  --baseline <项目目录>/.ios-workflow/tests/visual/home-light/baseline-v1 \
  --reviewed-by <实际审阅者> --review-reference <需求记录中的审阅引用>

swift <Skill目录>/scripts/visual_snapshot.swift compare \
  --image <本次截图.png> --context <本次实际环境.json> \
  --baseline <项目目录>/.ios-workflow/tests/visual/home-light/baseline-v1 \
  --output <项目目录>/.ios-workflow/artifacts/visual/<本次运行目录>
```

`record` 只保存经审阅的输入与声明，不表示测试通过；脚本无法证明声明的真实性，客户端仍须保留可核对的审阅记录。基线包含图片、环境、SHA-256 和审阅引用，应随项目同步。助手拒绝覆盖任何已有基线；需求预期改变时先审阅新候选，再创建 `baseline-v2` 并通过明确变更更新项目测试入口引用。

`compare` 核对基线完整性、环境相等、图片尺寸与点数×scale，然后按 sRGB RGBA 像素精确比较。退出码 `0` 表示图像一致；`1` 表示变化，输出 `diff.png`（变化像素为紫色）、`current.png` 和 `report.json`；`2` 表示基线缺失、工具/输入错误或环境不一致，不能当作通过。已有基线不会被改写，没有自动更新或放宽阈值选项；CI 必须传播退出码。输入无法读取等前置错误只输出原因，不能依赖必定存在报告。

图片差异先区分真实回归与环境/非确定性输入问题。未经审阅不得通过更新基线消除失败；视觉基线变更与实现变更共同 review。报告记录关联 Requirement/验收、受测输入与环境，仍按[验收证据规则](tracking-evidence.md)决定完成状态。日志与 diff 放项目 artifacts，规则包只保留通用模板和脚本。

## 已有 SnapshotTesting 项目

使用 [Point-Free SnapshotTesting](https://github.com/pointfreeco/swift-snapshot-testing) 的项目可保留原有 `assertSnapshot` 接口。依赖只加入测试 target，版本与锁文件遵循项目既有依赖方案；不擅自新增另一套包管理器。固定相同模拟器和 traits，CI 使用禁止录制/更新基线的模式；缺少基线应失败。首次录制产物仍需审阅，采用库提供的 diff 也必须保存真实结果。无需同时维护原生助手和该库的两套相同基线。
