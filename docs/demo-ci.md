# Demo 模拟器测试

GitHub Actions 的 `demo-tests` 在固定的 macOS 15 / Xcode 16.4 / iOS 18.5 / iPhone 16 Pro 上执行 `xcodebuild test`。`generated-builds` 的五组 `build-for-testing` 继续验证生成工程；两者分别报告，tag 发布必须同时通过。PR、main、tag 和手动运行均执行 Demo 测试，不按路径跳过发布所需验证。

脚本只复制 Demo 的 `project.yml`、App、Tests 和 UITests 到显式输出目录，用实际工程定义生成临时 Xcode 项目；不读取首次生成配置，不改业务项目或工作流内的追踪记录。Xcode、SDK、XcodeGen、scheme、设备与运行时、测试范围和退出状态写入 `test-report.json`。找不到指定版本或唯一可用设备时返回失败并记录环境阻塞，不自动改用其他环境。

本地按已安装环境填写参数，`DEVELOPER_DIR` 只影响本次命令；输出目录必须为空：

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
python3 scripts/check_demo_tests.py \
  --output /tmp/workflow-demo-tests \
  --expected-xcode 16.4 --runtime 18.5 --device-name 'iPhone 16 Pro'
```

通过条件包括 `xcodebuild` 退出状态为 0、存在可解析的 `.xcresult`、摘要和测试树数量一致、全部选中测试实际执行且通过、单元与 UI bundle 均存在。当前基线至少 11 项单元测试与 5 项 UI 测试，跳过、预期失败、零测试或缺失结果都不能算通过；合理调整测试套件时同步审查脚本基线。脚本无自动重试。

CI 发布简短 Job Summary，并保留 14 天的 JSON 摘要、测试树、失败日志和 `.xcresult`；临时项目与 DerivedData 不上传。大型产物仅保存在 runner 临时目录或业务项目忽略的 artifacts 目录，不进入工作流规则包。CI 结果证明 Demo 本次模拟器测试，不代表所有业务项目、真机或全部 iOS 版本验收。

环境来源为 [GitHub macOS 15 runner 清单](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md)。Xcode 结果接口可通过所选工具链的 `xcrun xcresulttool get test-results summary --help` 和 `tests --help` 查询；环境更新需一起调整固定版本并验证，不静默跟随 runner 默认 Xcode。
