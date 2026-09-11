# 商城首页验证

- 范围：推荐横幅、商品卡片、搜索、分类组合筛选、商品简介；保留计数、设置及运行时语言切换。
- 数据：4 件本地示例商品，价格为展示用途，无下单、购物车或支付服务。
- 环境：Xcode 26.6 (17F113)，iPhone 17 Pro 模拟器，iOS 26.5；scheme WorkflowDemo，Debug，无签名。
- 编译：build-for-testing 成功。
- 测试：xcodebuild test 成功，11 项单元测试、5 项 UI 测试，0 失败。
- 资源：12 种现有语言各新增 14 个商城键，plutil 语法检查及键一致性检查通过。
- 视觉：检查中文浅色、深色最大辅助字号首屏、阿拉伯语 RTL 首屏截图；未执行真机、iPad 或完整 VoiceOver 验收。
- 已有警告：LocalizationPolicy 的共享 preferenceStore 存在 Swift 严格并发警告，本次未修改其行为。
- 结果包：`.ios-workflow/artifacts/shop-tests.xcresult`；构建及测试日志、截图同在项目 artifacts 下并被忽略，跨设备需单独共享或重新验证。

## 当前受测输入 SHA-256

- `App/AppDelegate.swift`: `b647a374b04d6247134570b98e9632f99c6ebfb62c4d87330474179c38e710b3`
- `App/Core/Localization/AppLanguage.swift`: `3a1f84d3f34ff4b0239c9a808e3df9c19c20cd10999f26739a5c059c9c1fe103`
- `App/Core/Localization/LanguagePreferenceStore.swift`: `9441c99db42119f425133b6b07fd6711c65c313a65e855a8fe4afa56a8ae6426`
- `App/Core/Localization/LocalizationPolicy.swift`: `526955b9e32fb0d39fad31337c9960b981e9559b4823f9954512bd59befd7cc7`
- `App/DesignSystem/DesignTokens.swift`: `c8e943aa749d76d25b5d427c1ba9ea5d150ff3b28f2bc04ea9bd3666f1273374`
- `App/Features/About/AboutViewController.swift`: `43c677d0349cb0b35cf990adcc86c4e780c75e9e3b84e04cd383f2fa4bb986d1`
- `App/Features/Home/HomeViewController.swift`: `9fd98d5058acbe6ebb4fcff239533a065f7cd6face424323321c27ceba49c63d`
- `App/Features/Home/HomeViewModel.swift`: `32dfa1b6cd838d32ae4d9d040820860ca44bc3491b405ee42dea6ca3c127f3c9`
- `App/Features/Language/LanguageViewController.swift`: `5e281bc7b266f41c00a58ec437e45b06f989fbb2b49dc64065a9c3e1ef8747c7`
- `App/Features/Settings/SettingsViewController.swift`: `28913bc0afebb58c4265800e7c2d539b3f643791ead7b17bbb71b38d00e6a74b`
- `App/Resources/ar.lproj/Localizable.strings`: `f8320341e7409190287969656c580f4b0126bd82438088b963128bedd41c6b11`
- `App/Resources/de.lproj/Localizable.strings`: `ab27b5b9ebaa9891bed2e83c220c8bfc39e02f90547fd6a4f7b4dc57d6663896`
- `App/Resources/en.lproj/Localizable.strings`: `57c3c75bd497ce5608ed808e4d211b2fd9e5b3329e0d852ab775eb4f151dbbcd`
- `App/Resources/es.lproj/Localizable.strings`: `24986e0f62030110cf608cc36d2480e00ff9478df45101a9945ca90ecca6bdac`
- `App/Resources/fr.lproj/Localizable.strings`: `f39c53c66268b49d0cd2002c5055fb41b921ddfd9601d3663311ddcf5c62833e`
- `App/Resources/it.lproj/Localizable.strings`: `4a98470e9d26c47435be0544bd2c14ec164c8c3d57d7f5957ae74f7568722bed`
- `App/Resources/ja.lproj/Localizable.strings`: `3095b5467292039da8c7a3b7a77c47c6f0637bfffcfc123a0ca3cba7832c3805`
- `App/Resources/ko.lproj/Localizable.strings`: `f7b48cac1d29af1b58c257ff94840433dde21d058c84d1b093d57881b7821bc7`
- `App/Resources/pt-BR.lproj/Localizable.strings`: `d84f60cfaef00691e084d1f58b835a3183ca496b2924549eaa42598c5450b1ea`
- `App/Resources/ru.lproj/Localizable.strings`: `c5cbedcf3818e55e4087a2f9b8600f8808f05f84bb437491d0a46493130e58de`
- `App/Resources/zh-Hans.lproj/Localizable.strings`: `290de65164f78cdfbd16037766786118bdd626ee1fe72659e499139239b90bc7`
- `App/Resources/zh-Hant.lproj/Localizable.strings`: `b6a078825218f24dd24e57f5b0e07a2f9fc77c109f52bcc649bdff95ddcfd392`
- `App/SceneDelegate.swift`: `14f084d3ecb42a89fcffbd7b51a9efcf28d79f78b3a3b2bc598360018adc1eb9`
- `Tests/WorkflowDemoTests.swift`: `493af311a3bb2acd08080d6632000e2d78b23085160c9d5bd4a34ed576981fee`
- `UITests/WorkflowDemoUITests.swift`: `5f88db85abf2af601c607078c6daba96d1214c007393791ab0afee85f44d2398`
- `WorkflowDemo.xcodeproj/project.pbxproj`: `dafa7772caa8505b443b4ead7a18c5efa401325a0623fa32ae541676aea494fe`
