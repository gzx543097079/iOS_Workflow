# iOS 三方库与编译规范

## 依赖方式

- 依赖管理方式以 `config/defaults.jsonc` 的 `dependency_manager` 或项目现状为准：`pod`、`spm`、`carthage`、`none`。
- 不因示例或个人偏好虚构三方库；只有需求确实需要时才引入，并评估收益、体积、许可和系统方案。
- 新增或更新直接依赖必须使用明确、唯一的版本号，不使用范围、模糊匹配、分支或浮动版本。
- 提交对应锁定文件或解析文件，使团队和 CI 获得一致版本。

## 版本写法

- CocoaPods：使用精确版本，例如 `pod 'Alamofire', '5.10.2'`；禁止 `~>`、`>=`、`<=`、`>`、`<` 或未写版本。
- Swift Package Manager：使用 `.exact("1.2.3")` 或 Xcode Exact Version；禁止 `from`、range、`upToNextMajor`、`upToNextMinor`、branch 和 revision。
- Carthage：使用 `==` 固定版本，例如 `github "Alamofire/Alamofire" == 5.10.2`。
- 若工具本身生成传递依赖版本，不手工改写；仍需保存其锁定结果。

## 新项目、更新与编译

- 新项目创建后，根据选择的管理器完成首次安装或解析，再执行编译。
- 三方库版本变化后，先执行对应的定向更新或重新解析，再编译验证。
- 依赖操作必须在业务项目目录执行。命令不可用、解析或安装失败时停止编译并提示用户。
- 每次编译前执行对应的安装、解析或 bootstrap，确认锁定结果一致后再构建。

### CocoaPods

- 新项目、新增依赖和每次编译前使用 `pod install`，确认 `Podfile` 与 `Podfile.lock` 一致。
- 仅在明确更新某个库时使用 `pod update POD_NAME`，避免无目标地更新全部依赖。
- 使用 CocoaPods 的项目通过 `.xcworkspace` 编译。

### Swift Package Manager

- 新项目、依赖变化和每次编译前执行包解析；Xcode 项目使用 `xcodebuild -resolvePackageDependencies`。
- 编译前确认 `Package.resolved` 已生成且与清单一致。
- 解析冲突不得通过切换到分支、revision 或版本范围绕过，应报告冲突并确认精确版本。

### Carthage

- 新项目或精确版本变化后使用 `carthage update DEPENDENCY_NAME --use-xcframeworks`；首次解析多个已确定版本的依赖可统一 update。
- 每次编译前运行 `carthage bootstrap --use-xcframeworks`，不得手工编辑 `Cartfile.resolved`。
- 编译前确认构建产物或 XCFramework 已按项目约定集成。

### none

- 不执行三方依赖安装或更新；直接运行项目构建流程。出现三方库需求时，先让用户选择管理方式和精确版本。

## 输出控制

- 安装、解析和编译成功时，只报告命令结果、目标和必要摘要。
- 失败时保留能定位问题的相关日志尾部、失败目标和下一步建议，不回显无关的完整日志。
