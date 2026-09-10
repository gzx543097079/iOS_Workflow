# 项目建档与需求状态

在 iOS 业务项目首次建立需求记录、判断是否需要留档或登记首次执行时读取。先确认实际工程所属项目根；记录写入该项目 `.ios-workflow/`，不写入 Skill、发布包或共享工作目录。多个业务项目各自建档，不按客户端当前目录猜测归属。

## 项目内文件

所有记录中的文件引用均以业务项目根目录为基准，使用可跨设备解析的相对路径；不得用某台设备的绝对路径作为来源、实现或证据引用。

| 项目相对路径 | 内容 |
| --- | --- |
| `.ios-workflow/sources/` | 本次需求来源的项目内副本或可审阅快照，按版本保留 |
| `.ios-workflow/requirements/<Requirement-ID>.md` | 原始意图、范围、技术方案、步骤、变更及完成摘要 |
| `.ios-workflow/progress.json` | 全项目稳定验收项及来源、实现、证据和状态的唯一机器账本 |
| `.ios-workflow/index.jsonc` | 当前活动需求的紧凑恢复摘要 |
| `.ios-workflow/history.jsonc` | 需求首次执行顺序与当前状态 |
| `.ios-workflow/handoff.md` | 跨设备交接入口、环境差异、未保存或未交付内容和下一动作 |
| `.ios-workflow/tests/`、`.ios-workflow/evidence/` | 当前需求的测试计划、精简报告及必要证据 |

技术设计、发布记录等同样放在业务项目的 `.ios-workflow/` 对应子目录。源文档若已受项目 Git 管理可直接引用，无需重复复制；外部 Markdown、Word、PDF、表格或其他需求形式应保留项目内来源和章节、页码、表格行等定位。文档无法可靠读取的部分标记待补充，不猜测其内容。

首次生成项目时，先确定业务项目根目录，在该目录保存需求来源与本次生成配置，再执行生成；生成前可以先接入 Skill 或按已有授权用 Git 保存记录。调用生成器时显式允许项目记录和接入元数据，已有业务文件仍按生成规范处理，不能覆盖现有工程。生成配置仅用于首次生成；后续恢复、实现、测试或 review 依据实际工程和当前需求，不读取、不核对初始生成配置。配置中声明了某功能、生成了工程或测试骨架，都不表示功能已实现。

## 创建与状态

1. 执行整份需求文档、跨设备开发、跨会话、多阶段、跨模块、高风险、共享追踪或用户明确要求留档时必须建档。目标和验收明确、单轮可完成、无上述条件的低风险普通维护可只在上下文形成精简需求卡；执行本身不是建档条件。仅分析文档而未获准实施时不把文档的全部内容登记为已授权开发范围。
2. 首次记录按 [追踪模板](../../assets/templates/tracking/)创建索引、需求档案和 `progress.json`；需要交接时创建 `handoff.md`。运行记录不得回写模板。
3. Requirement ID 保持稳定且不复用。可使用 `REQ-YYYYMMDD-NNN-<8位随机标识>`，随机标识由 UUID 工具生成，避免离线设备同时分配同一 ID；旧的 `REQ-YYYYMMDD-NNN` 继续有效。索引 `last_requirement_id` 仅供取号参考，不是跨设备的唯一性保证。
4. 需求状态只使用 `draft`、`ready`、`in_progress`、`blocked`、`done`、`cancelled`。分析完成且实施所需信息充分时进入 `ready`；编码前按技术设计规范确定设计等级，设计状态须为 `approved` 或 `not_required`，开始实施时进入 `in_progress`。
5. 需求首次进入 `in_progress` 时，按项目台账的 `next_sequence` 追加执行记录并递增序号。一个需求只登记一次，已共享的顺序号不得重排、复用或删除。并行分支出现未共享的序号碰撞时保留两条需求，结合实际首次执行时间协调新条目的序号，并记录调整原因；不得丢掉其中一条。

初始化或首次执行时，四份关联记录通过[统一保存接口](tracking-resume.md#统一保存与中断恢复接口)校验候选后保存；旧文件不存在时显式提供 `None` 哈希，不从模板推断实际进度。

## 可机器核对的关联

- `history.jsonc` 保持 `version: 3`、`project: "."`、`next_sequence` 和 `execution_order`。每条执行记录包含 `id`、`file`（档案项目相对路径）、正整数 `sequence`、当前需求 `status`；可增加时间和说明字段。全台账需求 ID 和序号不得重复，`next_sequence` 必须大于所有已登记序号。未开始的 `draft`/`ready` 需求允许档案 `sequence: null` 且尚无执行记录。
- 选定需求的档案 frontmatter 使用已有的 `id`、`project`、`sequence`、`status`，与索引及执行台账一致。`current_step` 仍可只保留在正文恢复摘要；如果档案额外提供同名 frontmatter 字段，才与活动索引比较，不要求旧档案补字段。
- [tracking_state.py](../../scripts/tracking_state.py) 的 `validate_tracking_state(project_root, requirement_id=None)` 只读核对这些关系和选定需求的登记状态；不读取正文、无关历史档案或测试证据，不改状态。`metadata_only` 和 `checked` 不是业务验收成功；先处理 `errors`，再按当前任务检查实际工程与相关证据。
- 为避免额外 YAML 依赖，档案开头的 `---` 元数据仅支持平面 `key: scalar`：普通单行字符串、JSON 双引号字符串、YAML 单引号字符串（内部引号写作 `''`）、整数、`null`、`true`、`false`。允许空行和整行注释；带冒号的时间保持原样，含 `: ` 或行内注释的文字须加引号。不支持嵌套、集合、块值、标签或锚点，重复字段、复杂写法、缺失分隔符及超过 256 行/64 KiB 的元数据明确报错，不猜测解析或自动重写档案。正文不受此标量约束。

建立或变更验收账本时再读取[验收与证据](tracking-evidence.md)；需要生成工程时读取[项目生成](project-generation.md)。记录创建不代表相应需求已实现或已获外部操作授权。
