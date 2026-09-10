# NimbleFive 配置验证示例

输入为用户提供的 `NimbleFive-MVP-PRD.md` v1.0（2026-09-10）。未复制原 PRD，也不依赖用户 Downloads 路径运行测试。

`project.json` 是项目复制配置示例后按 PRD 修改并保存的完整项目实例。它可直接作为生成器的 `instance_path`，但本次不生成或开发实际 NimbleFive App。

| 需求 | 实例及处理 |
| --- | --- |
| Swift、SwiftUI、iOS 16 | `language`、`ui`、`deployment_target` |
| iPhone、竖屏、英语 | `target_devices`、`supported_orientations`、`supported_localizations` |
| 指定 Bundle ID、1.0.0 (1) | 标识和版本字段 |
| 流程测试 | 客户端开启 UI 测试 target；不是已完成业务测试 |
| 无后端、JSON 存档、纯 Swift 游戏规则 | `constraints`，待业务设计实现 |
| 广告、主题、10,000 种子验收 | `constraints`，基础生成器不自动实现 |
| MVVM、CocoaPods、系统深浅色 | 示例项目显式选择，来源明确，不冒充 PRD 决定 |

自动化测试验证实例加载、隔离、示例变化不影响项目实例、非法输入写入前拒绝、方向和语言等配置映射。测试生成的临时骨架仅验证生成器输出，结束后清理；不作为可交付业务 App。原 PRD 的业务验收尚未执行。


配置只用于首次生成。后续业务迭代以实际工程和需求为准，不再读取或核对本文件。
