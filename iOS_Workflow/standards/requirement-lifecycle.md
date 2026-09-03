# 需求生命周期与执行记录

运行状态保存在可见目录 `<工作目录>/iOSFlowRecords/`，不写入 `iOS_Workflow/`。一个工作目录包含多个项目时，以项目相对路径分组；每个项目在 `projects/<项目>/history.jsonc` 保存需求执行顺序。

高风险、跨模块或跨会话测试按 `standards/testing.md` 保存到 `tests/<项目>/`；需求档案只记录计划/报告路径和结论。恢复普通实现任务时不扫描测试目录，进入测试步骤后才读取当前 Requirement 对应文件。

## 创建与状态

1. 仅对用户明确要求留档，或跨会话、跨模块、多阶段、高风险、需要共享追踪的任务创建档案；执行本身不是建档条件。首次记录时按 `templates/tracking/index.jsonc` 创建索引，并按 `templates/tracking/requirement.md` 创建需求档案。
2. ID 使用 `REQ-YYYYMMDD-NNN`，当天从 `001` 递增；从索引的 `last_requirement_id` 取得当日末号，不扫描历史需求正文，不得复用已删除或取消的 ID。
3. 状态只使用 `draft`、`ready`、`in_progress`、`blocked`、`done`、`cancelled`。
4. 分析完成且无阻塞信息时进入 `ready`；开始实施时进入 `in_progress`；完成定义、验收和必要验证通过后进入 `done`。
5. 需求首次进入 `in_progress` 时，项目台账不存在则按 `templates/tracking/project-history.jsonc` 创建；从 `next_sequence` 取得顺序号并追加记录，再递增该值。需求只登记一次，顺序号不得重排、复用或删除。
6. 编码前按 `standards/technical-design.md` 确定设计等级；设计状态不是 `approved` 或 `not_required` 时不得进入 `in_progress`。

## 执行与恢复

- 步骤使用稳定的 `STEP-NNN`，写明目标、范围、前置条件、完成条件和验证方式。
- 需求档案维护紧凑的 `恢复摘要`，只包含当前步骤、下一动作、阻塞项、证据键和范围版本；详细过程不复制到摘要。
- 只在阶段边界、需求变更、阻塞、关键验证、提交、推送或结束时追加简短记录；同一阶段内的连续步骤合并记录，不保存完整命令、日志或 diff。
- 恢复任务时先读只含活动项的 `index.jsonc`，再优先读取当前需求档案的 frontmatter、`恢复摘要` 和首个未完成步骤，不默认读取完整档案。只有范围、设计或历史细节不足时才读取相关章节。核对项目路径、分支、HEAD 和工作区后继续。
- 实际 Git 状态与档案不一致时先记录差异；会改变实现或验收结果时向用户确认。
- 用户变更需求时保留原始需求，追加变更原因、范围影响和新增或取消的步骤。
- 索引只保留一个 `active_requirement` 摘要和 `last_requirement_id`；`done` 或 `cancelled` 后把活动项设为 `null`，历史只保留在项目台账和需求档案中。版本 1 的历史档案保持只读兼容，无需批量重写。
- 项目台账保留所有开始执行过的需求；完成、阻塞或取消只更新状态、时间、交付状态和最终提交，不改变顺序。查看历史时只读取该台账。

## Git 关联

- 提交正文加入 `Requirement: <ID>` 和 `Steps: <STEP-ID,...>`；无关联需求的维护提交说明原因。
- Git 交付使用独立的 `delivery_status`：`uncommitted`、`committed`、`pushed` 或 `not_applicable`，不反向决定需求是否验收完成。
- 提交成功后记录 hash、摘要、步骤和验证结果，并把交付状态更新为 `committed`；推送成功后更新为 `pushed`。已完成需求通过项目台账定位档案，不重新设为活动项。
- 阶段边界、提交和完成时同步更新需求档案与项目台账；活动需求存在时同步索引摘要。
- 推送成功后只记录远端、分支、提交或 tag；失败记录原因，不标记成功。

## 完成

仅当必要步骤和验收标准通过、相关测试完成、阻塞已处理且配置文档同步时标记 `done`。`done` 与 Git 提交、推送解耦；未提交的已完成需求保留 `delivery_status: uncommitted`，后续提交时再关联。完成摘要包含交付状态、实现内容、验证结果、遗留事项和下一建议。
