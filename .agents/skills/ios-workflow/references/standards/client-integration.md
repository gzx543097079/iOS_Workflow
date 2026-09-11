# 客户端调用入口

接入编辑器、命令行客户端或其他 AI 客户端时读取。统一使用 [workflow_client.py](../../scripts/workflow_client.py)，复用已有需求门禁、恢复摘要、事务保存和证据接口。运行环境为 macOS/Linux、Python 3，无额外依赖。

客户端负责在编码前、阶段保存和完成声明前实际调用入口，并处理非零退出状态。脚本不会拦截任意编辑器写入，也不运行测试、修改业务源码、提交或推送 Git。项目需求、进度、请求文件和证据仍保存在所属业务项目 `.ios-workflow/` 中；首次生成继续使用[项目生成](project-generation.md)接口，后续入口不读取或核对历史生成配置。

## 调用与返回

```sh
WF_CLIENT="/absolute/path/to/ios-workflow/scripts/workflow_client.py"
WF_PROJECT_ROOT="/absolute/path/to/MyApp"
python3 "$WF_CLIENT" resume --project-root "$WF_PROJECT_ROOT"
python3 "$WF_CLIENT" gate --project-root "$WF_PROJECT_ROOT" --request .ios-workflow/client/start.jsonc
```

`--project-root` 明确指定业务项目，请求文件和输出记录使用项目相对路径，禁止绝对路径、`..`、符号链接和生成配置路径；证据输入沿用现有证据接口的项目内路径校验。请求文件使用 UTF-8 JSON/JSONC 对象，重复字段、未知字段和缺少必需字段均报错；不要将完整文档作为命令行参数。

除 `--help` 外，标准输出为一行 JSON：

```json
{"schema_version":1,"command":"gate","ok":true,"result":{"gate_passed":true,"tracking_required":true,"decision":"tracked","phase":"start","metadata_only":true},"errors":[],"error_count":0}
```

- `ok=true` 对应退出码 `0`，表示该命令的检查或操作成功；否则退出码 `1`。参数错误也返回 JSON。
- `result` 保留命令结果；需求卡、四份候选全文及证据输入清单不回显。恢复结果按页返回登记摘要，按 `has_more`、`truncated` 和 `omitted` 继续读取。
- `errors` 最多展示 10 条，每条最多 400 字符；`error_count` 保留实际已发现数量，截断不等于没有其他错误。
- `prepared`/`complete` 仅描述保存事务；`metadata_only`、登记状态和哈希匹配都不代替业务验收。`capture` 成功可以保存实际失败的测试结果，不能将命令成功解释为测试通过。

## 命令契约

| 命令 | 输入 | 结果与处理 |
| --- | --- | --- |
| `gate` | `--request`：`task_kind`、`phase`、`card`；可选 `requirement_id` 及任务事实标记 | 调用 `assess_requirement_gate`；失败先补卡、建档或修复一致性 |
| `resume` | 可选 `--requirement-id`、`--max-items`（1～100，默认 20）、`--offset`（默认 0） | 调用 `load_resume_context`；省略 ID 只使用活动索引，不猜测最近任务 |
| `prepare` | `--request`：`requirement_id`、`candidates`、`expected_hashes` | 验证四份完整候选，返回 `transaction_id`；此时尚未替换当前记录 |
| `snapshot` | 必填 `--requirement-id` | 只读返回现有四份记录的 SHA-256 和登记状态；不返回完整记录 |
| `prepare-update` | `--request`：`requirement_id`、`updates`、`expected_hashes` | 在本地合并已有字段，使用现有事务准备候选，返回事务 ID 和修改文件列表 |
| `apply` | `--transaction-id` | 应用已准备事务；冲突或中断返回失败并保留恢复资料 |
| `recover` | `--transaction-id` | 显式继续选定事务，重新核对全部目标和登记输入 |
| `abandon` | `--transaction-id` | 放弃选定事务，不回滚当前文件；`requires_reconciliation=true` 时先协调部分写入 |
| `capture` | `--request`：`evidence_path`、`input_paths`、`environment`、`result`，可选 `recorded_at`；另提供 `--output` | 根据已有文件计算证据元数据，保存到新的 `.ios-workflow/evidence-records/*.json`，返回路径和数量摘要；拒绝覆盖旧记录 |
| `compare` | `--request`：`record_path`、`current_environment`、`current_input_paths` | 本地读取证据记录再核对；只有 `matched` 返回成功，`stale`/`unknown` 均失败 |

`gate` 的 `phase` 为 `start`、`checkpoint` 或 `complete`，`task_kind` 为 `feature`、`bug` 或 `maintenance`。可选任务事实标记为 `low_risk`、`single_turn`、`acceptance_clear`、`continuity_required`、`related_requirement`，均必须是布尔值。标记由客户端按当前任务与已有约定提供，接口不推断事实真实性，也不接受把新增功能改称纯维护来绕过追踪。

开始请求示例：

```json
{
  "task_kind": "feature",
  "phase": "start",
  "requirement_id": "REQ-20260911-001-example",
  "card": {
    "goal": "在已有首页增加商品分类筛选",
    "scope": ["分类切换", "空结果提示"],
    "acceptance": ["选择分类后仅显示该分类商品；无匹配商品时显示空状态"],
    "exclusions": ["下单和支付"],
    "assumptions": ["商品来自项目已有数据源"]
  }
}
```

ID 必须来自实际建档，示例不能直接作为已存在记录。完整门禁要求见[需求定义](requirements.md)，四文件候选、旧哈希及冲突处理见[统一保存与恢复](tracking-resume.md#统一保存与中断恢复接口)。`prepare` 保持现有接口契约：客户端在本地保留未修改记录，提交完整候选文本与观察到的四个旧文件 SHA-256；文件确实缺失时才填 `null`。

证据环境须记录实际 `xcode`、`sdk`、`scheme`、`configuration`、`destination`、`test_selection`；证据路径位于项目 `.ios-workflow/`，输入集合覆盖真实受影响文件。`capture` 不读取测试报告并判定通过，客户端须先核对实际执行结果；其输出文件中的对象可由客户端本地读取并放入关联验收项的 `evidence` 数组。`compare` 的当前环境和当前输入集合也须重新观察，不能把旧记录复制成“当前值”。详见[测试](testing.md)与[验收及证据](tracking-evidence.md)。

## 本地合并已有记录

编辑已有需求前先 `snapshot --requirement-id <实际ID>` 保存四份旧哈希。客户端在本地保留这些观察值，构造 `prepare-update` 请求；不要把完整账本和证据清单传入模型再重写。下面只展示请求的 `updates` 部分，实际请求同时包含需求 ID 和观察到的 `expected_hashes`：

```json
{
  "items": [{"id": "实际验收ID", "set": {"status": "implemented"}}],
  "active_requirement": {"next_action": "运行受影响测试"},
  "archive": {"append": "本阶段已实现，尚未验证。"}
}
```

- 省略的字段原样保留；提供的数组只替换对应字段。新证据由客户端从本地 `capture` 输出文件读取后合并，不能因省略旧失败结果而推断通过。
- `items` 更新本需求已有验收 ID；`active_requirement` 更新本需求当前摘要；`history_entry` 更新已存在执行行；`archive.metadata` 仅更新平面标量元数据，`archive.append` 只追加正文。稳定 ID、归属、档案路径和执行序号不可变。未知新字段拒绝，扩展格式或新增验收项使用完整候选接口。
- 终态由客户端根据真实验收显式提供：活动索引置 `null`，同时更新 `history_entry.status` 和 `archive.metadata.status`；脚本不会自行提升状态。缺失或矛盾的终态与证据仍被原校验拒绝。
- `prepare-update` 只准备事务，随后显式 `apply`；中断使用相同 `recover`。旧版本已变时拒绝，先检查外部修改和实际事实，再重新观察版本；不能自动重新取哈希覆盖别人的更新。
- 保持原账本和证据 schema，不迁移历史项目。首次建档及复杂文档改写沿用 `prepare`，完成事务的清理仍遵循项目保留约定。

## 阶段串联

1. 首次需求按[建档规范](tracking-start.md)准备项目内来源和四份记录，`prepare` 后 `apply`；已有需求先 `resume`，核对实际分支、工程及必要环境。
2. 编码前调用 `gate`，`phase=start`。门禁失败时修复缺失或不一致记录；不能依靠忽略退出码继续实现。
3. 完成相关实现与真实验证后，按需 `capture`；复用旧证据先 `compare`。在本地合并本次事实，`prepare` → `apply` 保存，再以 `phase=checkpoint` 检查。测试失败也可以保存真实 `implemented`/`blocked` 状态与失败证据。
4. 仅在验收满足后将四份候选同步为终态，`prepare` → `apply` 后调用 `gate`，`phase=complete`；再结合实际业务验收给出完成结论。
5. 中断后读取项目记录及事务 ID，显式 `recover`。冲突不能通过覆盖或删除事务目录解决；放弃旧候选时先 `abandon`，协调当前四份文件后准备新事务。跨设备仍按[同步规范](tracking-sync.md)处理 Git 与环境差异。

客户端可通过 `subprocess.run([...], capture_output=True, text=True)` 读取 JSON，同时检查返回码与 `ok`；失败结果交给调用方处理，不继续依赖该检查的后续动作。是否存在可靠的客户端调用钩子须以实际宿主能力为准，不宣称仅安装 Skill 就能保证所有写入经过门禁。
