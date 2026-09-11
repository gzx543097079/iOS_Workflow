# 验收项、证据与完成

在 iOS 业务项目登记或变更验收、复用验证结果、相关 review 或判定完成时读取。以项目 `.ios-workflow/progress.json` 为唯一验收账本，档案按 ID 引用；来源、实现与证据均用项目根目录相对路径，实际记录不写入 Skill 或共享目录。

## 来源、范围与逐项验收

1. 不要求输入是某一种 PRD 模板。先识别文档版本、原始目标、已授权范围和优先级，再按实际内容提取功能、异常状态、非功能要求、技术限制及交付条件。P1、非目标和当前未授权事项保留定位与范围决定，不静默纳入本次实施，也不直接删除。
2. 为每个可独立验收的要求分配稳定 ID，例如 `<Requirement-ID>-AC-001`。在 `.ios-workflow/progress.json` 中记录 `id`、`requirement_id`、`source.path`、`source.section`、`criterion`、`status`、`implementation` 和 `evidence`。`criterion` 使用可观察的“条件—操作—结果”；纯技术限制说明可验证的边界。需求档案按 ID 引用账本，不另维护一套可能分叉的验收状态。
3. 每条原始要求应映射到验收项或有来源的排除决定；拆分或合并时保留旧 ID 与关联，新需求增发 ID，不覆盖原始要求。用户变更、批准延期或取消时记录原因、决定来源、影响范围和步骤；AI 不能为了凑齐完成率自行将未完成项改为延期或取消。
   `deferred`/`cancelled` 验收项在账本提供 `scope_decision: {"reason": "决定理由", "source": {"path": "项目内决定来源文件", "section": "章节或锚点"}}`，用于定位已有范围决定。旧记录如只在正文保留决定，核对真实来源后补此关联，不自动编造理由；机器只检查来源引用和理由存在，不能据此认定已经取得用户授权。
4. 验收项状态使用 `pending`、`in_progress`、`implemented`、`verified`、`blocked`、`deferred`、`cancelled`。`implemented` 仅表示已有对应实现；`verified` 必须有实际取得、适用于当前实现和验收条件的成功证据。未知、未运行、无法读取或无法访问证据，都不能推断为已验证。
5. `implementation` 只登记实际存在的项目相对文件路径；测试名、符号和行号等定位写入额外说明。规则或文档类验收可指向实际落实规则的文件，不能为满足字段而虚构源码。
6. `evidence` 每条记录包含项目相对 `path`、文件实际 `sha256` 及非空 `inputs: [{path, sha256}]`，并提供非空字符串 `environment`（简短实际环境说明）、`result`（`passed`/`failed`/`blocked`/`skipped`）和含时区的 ISO 8601 `recorded_at`。`verified` 的所有当前证据必须为 `passed`；历史记录缺字段明确待补证，不自动迁移或猜测。证据文件放在项目 `.ios-workflow/` 下；当前证据的输入集合须覆盖来源文件和全部实现文件，并按影响加入工程文件、依赖锁等内容。`capture_evidence` 的输入 `environment` 是字段对象，输出记录中的 `environment` 则为摘要字符串，完整字段保存在 `environment_fingerprint.values`；优先使用接口生成记录，不能把输入对象直接写到账本的字符串字段。记录真实测试范围、结论、环境和未覆盖项；哈希只能由实际文件计算，不能手填示例值或编造成功日志。
7. 按测试规范检查证据是否适用：源码、依赖或相关环境变化导致原结论失效时，受影响项退回 `implemented` 或 `blocked`，将旧证据移出当前 `evidence` 数组，存入 `archived_evidence` 或历史报告并安排最小复验；纯文档或运行记录变化不使无关测试失效。仅有报告文件及正确哈希不能证明业务正确，仍要审阅报告与验收的对应关系。
8. 完成、交接和相关 review 前，由客户端读取项目 `.ios-workflow/progress.json`，调用 [progress_validation.py](../../scripts/progress_validation.py) 的 `validate_progress_scope(project_root, progress, requirement_ids=[...], item_ids=[...])` 检查本次相关条目的路径、证据及登记输入，并保留全账本 ID 唯一性和有效需求关联检查；仅显式全项目健康检查调用 `validate_progress(project_root, progress)`；返回非空错误列表时处理相关错误，不报告校验通过。此接口只做结构核验，不代替业务验收，也不会自动把项目或功能标记完成。

## 完成

仅当本次已授权范围内的必要步骤完成，所有必需验收项有当前适用的成功证据，必要测试通过，阻塞已解决，且需求、实现与相关文档一致时标记 `done`。延期、取消和非目标必须有范围决定，不能通过删除失败项制造完成；初始生成配置不属于后续完成核对项。

完成时同步项目内需求档案、账本与台账，并清空对应活动索引。完成摘要列出已验证的验收 ID、实现、验证结果和范围外遗留事项。`done` 与 Git 提交、推送解耦；“功能已完成”和“代码及进度已同步到远端”分别报告，Git 交付不重新激活已完成需求。

验收状态或完成结论涉及四份关联记录时，用[统一保存接口](tracking-resume.md#统一保存与中断恢复接口)提交完整候选与实际旧文件哈希；先取得当前适用的真实证据，保存接口不会生成成功结论。

更新后可用 [tracking_state.py](../../scripts/tracking_state.py) 的 `validate_tracking_state(project_root, requirement_id)` 核对选定需求的档案、台账、索引和账本状态是否一致。`done` 若仍含未验证项、缺少登记成功证据的 `verified` 项或无来源决定的延期/取消项，须处理错误；已 `done`/`cancelled` 的活动索引必须清空。此项只检查登记事实，不替代上面的相关证据校验。

实际执行测试时读取[测试规范](testing.md)；只有需要交接或确认 Git 同步时读取[跨设备与 Git](tracking-sync.md)。
