# ADR-0001：使用 XcodeGen 生成 Xcode 工程

- 状态：已接受
- 日期：2026-09-03

## 背景

工作流需要从声明式配置生成 Swift/UIKit、Swift/SwiftUI 和 Objective-C/UIKit 工程。直接拼接 `project.pbxproj` 容易产生对象引用、构建设置和 Xcode 版本兼容问题，同时难以通过文本 review 判断工程结构。

## 候选方案

1. 直接生成 `project.pbxproj`：不依赖额外工具，但格式脆弱、维护和验证成本最高。
2. 保存固定 `.xcodeproj` 模板再替换字段：实现简单，但组合增加后模板易漂移，旧工程设置也容易残留。
3. 生成 XcodeGen `project.yml`，再由 XcodeGen 创建工程：配置可读、可测试，能统一三种组合，但执行环境需要安装 XcodeGen。

## 决策

采用方案 3。内部生成器先校验配置并输出确定性的 `project.yml` 和源码，再调用 XcodeGen。未安装 XcodeGen 或未生成唯一工程时明确失败，不尝试手写或修补 `project.pbxproj`。

## 影响

- `project.yml` 成为工程结构的可 review 来源，生成器测试覆盖所有支持组合。
- 新项目环境需要提供 XcodeGen；依赖工具缺失时保留配置和源码用于排查，但不得继续编译。
- 若未来 XcodeGen 无法满足工程需求，可保留生成配置接口并替换后端；回退不改变 `defaults.jsonc` 和 DesignTokens 格式。
