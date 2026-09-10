# iOS 发布与分发

已有项目及后续版本以当前工程、源码、依赖、设计系统和需求为准；不读取或核对首次生成配置。

归档、导出、上传 TestFlight、提交 App Store 审核或发布版本时读取。目标是让同一份已验证源码可追溯地进入目标渠道，并把“上传成功”“审核通过”和“用户可用”作为不同状态处理。

## 权限边界

- 本地预检、构建、归档、校验和生成发布材料属于可逆准备工作，可在发布任务范围内执行。
- 上传构建、添加测试人员、提交审核、修改商店元数据、开始或暂停发布会改变外部状态；只有用户当前要求已经明确包含对应动作时才执行。
- 不创建、猜测或替换 Team ID、证书、描述文件、App Store Connect App、API Key 和账号角色。缺失时标记阻塞并列出所需信息。
- 证书私钥、描述文件、API Key 和登录凭据只从 Keychain、CI Secret 或团队批准的密钥系统读取，不写入仓库、模板、命令参数或日志。

## 发布输入

开始前确认：

- 目标 App、Bundle ID、Team、工程或工作区、Scheme、Release Configuration 和目标渠道。
- Marketing Version、唯一递增的 Build Version、源提交或 Tag，以及依赖锁文件。
- 渠道为内部测试、TestFlight 内测、TestFlight 外测、App Store、Ad Hoc 或 Enterprise；不要把不同渠道共用一份未经确认的导出配置。
- 发布说明、测试说明、支持与隐私链接、审核备注、可用地区、发布时间和负责人。
- 发布方式为手动、定时或分阶段，以及上线监控、停止条件和热修复负责人。

## 发布前检查

1. 源提交、Tag、版本号和依赖锁定一致；工作区无意外修改，Release 配置不包含调试开关、测试服务器或开发证书。
2. App Store 分发前确认 App Store Connect 已存在对应 App 记录；所有 target 和 extension 的 Bundle ID、Team、Capability、Entitlement、证书与描述文件一致。
3. 在计划发布的源码和生产配置上完成静态检查、受影响 target 编译、自动化测试和关键真机冒烟；测试证据必须对应本次源提交、版本和 Build。
4. 检查 Privacy Manifest、权限用途说明、出口合规、App 隐私信息、年龄分级、截图、描述、支持链接、法律信息和适用的订阅或内购配置。
5. 确认仓库、归档、导出目录和日志中没有密钥、私钥、生产令牌、个人数据或完整敏感日志。

## Archive 与校验

1. 优先使用项目已有发布脚本或 CI；否则使用显式的 workspace/project、scheme、`Release` configuration、`generic/platform=iOS` destination 和固定 `archivePath` 执行 `xcodebuild archive`。
2. 记录源提交或 Tag、Xcode 版本、Scheme、Configuration、Marketing Version、Build Version、Archive 路径和时间。Archive 生成后视为不可变产物，任何源码、配置、依赖或版本变化都重新归档。
3. 用 Xcode Organizer 或团队已有自动化完成 Archive 校验。模拟器构建、普通 Debug 构建或未经校验的 Archive 不作为商店发布产物。
4. 成功只记录命令类别、状态和证据位置；失败只保留首个可行动原因和必要上下文。

## 导出与上传

- 每个渠道使用经过团队确认的 `ExportOptions.plist`；不在规则或模板中硬编码证书名称、描述文件 UUID、Team ID 或账号信息。
- TestFlight 和 App Store 构建可通过 Xcode、Transporter 或项目已有 CI 上传。API Key 只通过 Keychain、CI Secret 或环境注入，且不打印值。
- 上传后等待 App Store Connect 处理完成并核对 Bundle ID、版本、Build、签名、符号和合规状态。上传命令成功不等于构建已可测试、可送审或已发布。
- 保存 App Store Connect 中的 Build 标识和处理状态，不把完整上传日志或凭据写入发布报告。

## TestFlight

1. 先向内部测试组分发，完成安装、启动、登录、升级、核心业务、推送及适用的购买恢复冒烟。
2. 外部测试前补齐 Beta App 信息、测试说明、联系信息和出口合规；需要 Beta App Review 时等待审核通过后再扩大发布。
3. 明确测试组、设备或系统覆盖、反馈渠道、测试期限和晋级标准；记录崩溃、反馈与已知问题。
4. 只有晋级标准满足且目标 Build 未变化，才将同一 Build 用于 App Store 提交；Build 变化后重新执行相应验证。

## App Store 提交与发布

1. 选择已处理并通过验证的 Build，复核版本元数据、App 隐私、出口合规、价格与可用地区、审核备注及适用的内购或订阅。
2. 只有用户明确要求提交审核时才执行提交；被拒后先记录原因和影响，不擅自扩大功能范围或更换合规声明。
3. 手动发布、定时发布或分阶段发布必须明确选择。审核通过不等于已向用户发布，需继续跟踪版本状态。
4. 发布完成后记录版本、Build、源提交或 Tag、发布时间、渠道、商店状态和负责人。

## 监控与回退

- 上线后监控崩溃、卡死、启动、登录、购买、核心业务指标、服务端错误和用户反馈；每项设置观察窗口、负责人和触发阈值。
- 可用的止损方式包括暂停分阶段发布、关闭服务端 Feature Flag、停止活动流量、修复后提交更高 Build。已安装的 App Store 二进制不能直接降级，不能把“回滚”描述为恢复旧二进制。
- 高风险版本发布前准备热修复分支、版本递增方案、服务端兼容窗口和用户沟通方案。
- 发布报告状态只使用 `prepared`、`archived`、`uploaded`、`testing`、`in_review`、`released` 或 `blocked`，并说明尚未完成的下一状态。

## 停止条件

出现以下任一情况时停止进入下一阶段：测试或 Archive 校验失败；签名、角色、协议或 App 记录缺失；Build 仍在处理或状态异常；隐私、合规、元数据或内购信息不完整；源提交与验证证据不一致；执行外部动作但没有明确授权。
