# 已留档需求的执行与恢复

继续、变更、阻塞或结束 iOS 项目的执行阶段时读取。只使用所属业务项目 `.ios-workflow/` 的活动摘要、相关验收与必要档案；记录不写入 Skill 或共享目录。需求状态与验收状态分开维护，不从聊天记忆推断进度；后续不读取、不核对初始生成配置。

## 执行与恢复

- 步骤使用稳定的 `STEP-NNN`，写明目标、范围、关联验收 ID、前置条件、完成条件和验证方式。
- 活动索引维护紧凑恢复摘要：当前步骤、下一动作、阻塞项、证据键、范围版本、分支和已观察到的基线。需求档案保留同样的恢复摘要作为回退；详细日志不复制到索引。
- 只在阶段边界、需求变更、阻塞、关键验证、交接或结束时更新相应记录；同阶段连续动作合并，不保存完整命令历史、冗长日志或 diff。
- 恢复任务先读项目内 `index.jsonc`、相关 `progress.json` 条目和有交接时的 `handoff.md`，再核对实际项目、分支、HEAD、工作区、依赖锁和所需环境。摘要不足时才按章节读取当前需求档案，不默认读取完整档案。进入测试步骤后才读取当前 Requirement 对应报告。
- 客户端可调用 [resume_context.py](../../scripts/resume_context.py) 的 `load_resume_context(project_root, requirement_id=None, max_items=20, offset=0)` 提取当前需求的分页摘要、登记状态、阻塞、下一动作及必要文件路径。基础摘要合法后，复用已读取的索引和账本，补读执行台账关联元数据及选定需求档案的平面 frontmatter，核对状态、ID、序号和已记录的步骤关系；不读档案正文、无关历史档案、报告内容或生成配置。选定需求全部验收项的 `done` 状态一致性不受分页限制；不是重新执行验证。
- `metadata_only`、`recorded_status` 与 `tracking_state_checked` 均不代表业务验收通过。先处理 `errors`，按 `has_more` 翻页；`truncated=true` 时依据 `truncated_fields` 和 `omitted` 按需回源读取完整字段，不把被省略内容当作不存在。档案使用[建档规范](tracking-start.md)定义的标量 frontmatter；旧档案不需要为步骤核对新增字段。需要复用证据时再按相关验收范围核验。
- 档案与实际文件不一致时以可验证事实为准，记录差异并降低无法证实的完成状态。不能把聊天记忆、另一设备的绝对路径、旧分支的通过结果或“上次应该做完了”当作当前证据。影响产品范围或验收的决定缺失时只暂停依赖该决定的部分。
- 索引只保留一个 `active_requirement` 和 `last_requirement_id`；`done` 或 `cancelled` 后清空活动项。所有已执行需求仍在台账和档案中；查看顺序只读取台账。
- 旧版共享目录及 `projects/<项目>/history.jsonc`、`requirements/<项目>/` 等记录保持只读兼容，无需批量改写，也不据旧记录自动认定当前完成。续做时把当前需求必要内容复制到所属业务项目目录，核对相对路径、实现和证据后继续；后续只写项目内记录，旧生成配置仍仅为历史资料。

## 统一保存与中断恢复接口

阶段边界需要一起更新索引、账本、台账和选定需求档案时，客户端使用 [tracking_update.py](../../scripts/tracking_update.py)：

```python
transaction_id = prepare_tracking_update(project_root, requirement_id, candidates, expected_hashes)
result = apply_tracking_update(project_root, transaction_id)
```

- `candidates` 为项目相对路径到完整 UTF-8 文本的对象，必须恰好包含 `.ios-workflow/index.jsonc`、`.ios-workflow/progress.json`、`.ios-workflow/history.jsonc` 和本次 `requirement_id` 对应的 `.ios-workflow/requirements/*.md` 档案。`expected_hashes` 使用相同四个键，值为编辑前实际完整文件字节的 SHA-256；只有文件不存在时使用 `None`，允许初始化。不能用摘要、选中段落或旧会话中的哈希代替完整旧文件。
- `prepare` 先核对旧哈希和记录保留关系，再用候选调用 `validate_tracking_state` 与本需求范围的 `validate_progress_scope`；核验的实际档案必须就是四个候选中的档案。已有验收 ID 不得删除或转属，其他需求的验收项和执行行不得修改或新增，已有执行序号、顺序与已分配的 `next_sequence` 不得倒退或复用。范围变化保留有依据的延期/取消项；跨分支序号协调仍按[同步规则](tracking-sync.md)处理。
- 只复制四份候选及选定需求引用的必要文件用于校验，不加载无关历史证据或生成配置。准备成功后移除输入副本，仅保留 `.ios-workflow/transactions/<transaction_id>/` 下的四份候选、`journal.json` 和实际输入哈希。状态与证据结论由调用方根据实际执行提供；保存成功及 `metadata_only` 都不是业务验收，接口不运行测试、不自行提升完成状态。
- `apply`/`recover` 在写入前一次核对全部目标只能处于记录的旧版本或新版本，并核对项目中实际输入哈希；逐文件替换前再次核对目标，写完后复查全部目标与输入才登记 `complete`。输入变化、外部编辑或写入中断时抛出错误并保留待恢复资料，不能报告保存完成；完成后的幂等调用只接受目标仍为记录的新版本。
- 检测到冲突时先检查当前四份文件和输入，不直接覆盖外部内容。不能继续旧候选时显式 `abandon`：只添加放弃标记，保留 journal 和候选，不回滚、不改当前文件。部分写入仍可能存在，须先逐项核对并整理完整候选、重新读取当前哈希，再 `prepare` 新事务。不得删除待恢复目录作为解锁手段。完成或放弃的资料可在当前记录已核对并同步后，按团队保留约定归档；本接口不自动清理历史事务。
- 锁使用 macOS/Linux 的 POSIX `flock`，进程退出后由系统释放，只协调本机遵守同一接口的写入者。四文件更新不是一次原子操作；编辑器不遵守此锁，仍可能在最后检查与替换之间修改文件，因此应用时停止并行编辑。此锁不解决跨设备 Git 冲突，恢复记录须随对应项目状态一起核对；不得因某设备有完成标记就跳过实际文件检查。

复用证据、变更验收范围或判定完成时再读取[验收与证据](tracking-evidence.md)；切换设备或核对同步状态时读取[跨设备与 Git](tracking-sync.md)。
