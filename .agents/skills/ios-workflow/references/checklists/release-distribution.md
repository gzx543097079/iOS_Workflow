# 发布与分发 Checklist

- [ ] 目标渠道、版本、Build、Bundle ID、Team、Scheme、Release Configuration、源提交或 Tag 已确认。
- [ ] 依赖已锁定，工作区无意外修改，发布配置不含调试开关、测试服务或敏感信息。
- [ ] 所有 target 与 extension 的签名、Capability、Entitlement、证书和描述文件一致。
- [ ] 静态检查、Release 编译、自动化测试和关键真机冒烟证据对应本次源提交、版本与 Build。
- [ ] Archive 已记录并校验；源码、配置、依赖或版本变化后没有复用旧 Archive。
- [ ] ExportOptions 与目标渠道一致，证书私钥、API Key、令牌和个人数据未进入仓库、模板、命令或日志。
- [ ] App Store Connect 的 App 记录、构建处理状态、隐私、出口合规、元数据、截图、链接、年龄分级及适用的内购配置完整。
- [ ] TestFlight 测试组、说明、冒烟结果、反馈渠道和晋级标准明确；未使用 TestFlight 时标记 `➖`。
- [ ] 提交审核、添加测试人员、修改元数据或开始发布等外部动作均在用户明确要求的范围内。
- [ ] 发布方式、观察指标、阈值、负责人、止损方式和更高 Build 热修复方案已明确。
- [ ] 上传、处理、测试、审核和发布状态分别记录，没有把上传成功当作发布完成。
