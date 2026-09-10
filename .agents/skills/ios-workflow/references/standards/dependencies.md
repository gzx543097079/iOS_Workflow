# 三方库与编译规范

## 通用

- 首次生成按本次输入的 `dependency_manager` 选择管理器；已有工程按实际工程定义、依赖清单、锁文件和项目约定维护，不读取生成配置。引入前评估系统方案、收益、体积和许可，不擅自更换管理器或虚构依赖。
- 已有工程接入、工程结构或依赖变化、构建环境不明时按[已有工程维护](existing-project.md)确认修改来源；管理器与工程入口已明确的重复构建不额外加载。
- 直接依赖必须是唯一精确版本，提交锁定文件。禁止范围、比较式浮动、通配符、分支、revision、commit、`latest` 或省略版本。
- 新项目和依赖变化后完成安装或解析再编译。编译前确认依赖一致；本任务内清单、锁定文件和环境未变且已有成功证据时复用，不重复执行。
- 命令不可用、解析或安装失败时停止编译并报告。

## 管理器

- CocoaPods：`pod 'Name', '1.2.3'`；新建、新增或需要同步时运行 `pod install`，指定升级才运行 `pod update NAME`；提交 `Podfile.lock`，通过 `.xcworkspace` 构建。
- SPM：使用 `.exact("1.2.3")` 或 Xcode Exact Version；需要同步时运行 `xcodebuild -resolvePackageDependencies` 并提交 `Package.resolved`。不得用浮动版本绕过冲突。
- Carthage：使用 `github "Owner/Library" == 1.2.3`；版本变化时定向 `carthage update NAME --use-xcframeworks`，需要同步时 `carthage bootstrap --use-xcframeworks`；提交且不手改 `Cartfile.resolved`。
- none：不运行依赖命令；需要三方库时先确认管理器和精确版本。
