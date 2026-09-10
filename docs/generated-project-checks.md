# 生成工程的编译检查

工作流发布前必须实际编译生成结果。Python 测试验证配置、路径、状态与打包契约；生成编译检查验证源码和 Xcode 工程设置能否被工具链接受，两者都通过后才创建 GitHub Release。

## 矩阵

| case | 语言与 UI | Swift 语言模式 |
| --- | --- | --- |
| swift-uikit-5 | Swift / UIKit | 5 |
| swift-uikit-6 | Swift / UIKit | 6 |
| swiftui-5 | Swift / SwiftUI | 5 |
| swiftui-6 | Swift / SwiftUI | 6 |
| objc-uikit | Objective-C / UIKit | 不应用 Swift 设置 |

全部用例显式生成单元测试及 UI 测试 target，并开启手动外观策略以覆盖相应模板。使用无第三方依赖的临时夹具，不读取任何业务项目的历史生成配置。`build-for-testing` 编译源码及测试 target，不执行 App 或测试，不据此宣布业务验收通过。

## 本地运行

需要完整 Xcode、iOS Simulator SDK 和 XcodeGen。工具缺失、环境不可用或编译失败都会返回非零退出状态，不能跳过后报告通过。

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer python3 scripts/check_generated_projects.py --case swift-uikit-5 --output /tmp/ios-workflow-swift-uikit-5
```

对表中每个 case 使用新的空输出目录；已有文件或旧结果不会被覆盖或复用。报告和日志位于生成夹具项目内 `.ios-workflow/artifacts/`，记录实际工具版本、SDK、命令和退出码；成功只输出摘要，失败提取相关错误。

## CI

主分支 push、PR、手动触发和版本 tag 都执行验证；仅版本 tag 可以进入发布。Release job 同时依赖 Linux Python 测试和全部 macOS 编译矩阵，任一失败就不创建 Release。

编译使用 GitHub 的 `macos-15` runner 和其已选择的 Xcode，实际版本保存在每次报告中。该镜像安装的软件以 [GitHub runner 镜像说明](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md)为准；镜像会更新，因此不会用镜像名称代替实际工具链证据。
