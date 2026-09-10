# 模块加载与 Token 评测

维护工具 `scripts/evaluate_module_loading.py` 用真实工具事件评估加载范围，位于仓库 `scripts/`，不加入日常 Skill 路由或团队分发包。它不会根据提示词、最终回答或文件名搜索结果推断“已经加载”。

`tests/fixtures/module-loading-cases.json` 的 `expected_modules` 是预先定义的断言，不是运行结果。当前 9 个案例覆盖已有 App 加新版本 PRD、低风险代码修改、首次生成、同设备恢复、跨设备恢复、失败阶段保存、纯推送、工作流 ZIP 发布和非 iOS 文档。已有 App 案例包含 XcodeGen 生成的工程文件；所有工程、需求和状态均为隔离测试夹具，不是实际业务验收。

同设备恢复只要求恢复规则；明确换设备时按恢复规则组合加载同步规则。这两个场景分开固定期望，不能因为一次输出不同就修改期望来让评测通过。生成前和已有项目迭代也使用不同输入与禁止加载列表。

## 导入已有真实事件

从 `codex exec --json` 保存 JSONL，然后运行：

```sh
python3 scripts/evaluate_module_loading.py evaluate \
  --case resume-only \
  --trace /path/to/events.jsonl \
  --project-root /path/to/the/evaluated/project \
  --output /path/to/new-report.json
```

`--project-root` 必须是事件发生时的项目目录；默认 Skill 路径为它下面的 `.agents/skills/ios-workflow`，其他安装位置用 `--skill-root` 指定。导入操作不启动模型。输出文件已存在时拒绝覆盖。

报告分开保存 `expected` 与 `actual`，列出实际读取模块、缺少的必需模块、禁止或额外加载、重复读取次数、不可观察操作和 trace SHA-256。退出码 `0` 表示观察完整且通过，`1` 表示观察到明确违反断言，`2` 表示无法判定；不能将缺少事件当成通过。

## 执行一个真实只读探针

先检查本机 `codex --help`、`codex exec --help` 是否支持以下参数。本次核对版本为 `codex-cli 0.153.4`。每次显式运行一个案例，不自动消耗用量跑完整矩阵：

```sh
python3 scripts/evaluate_module_loading.py run \
  --case resume-only \
  --output /tmp/ios-module-evaluation/new-resume-run \
  --timeout 120
```

工具复制当前 Skill 和案例文件到新的隔离目录，调用 `codex -a never exec --sandbox read-only --skip-git-repo-check --ephemeral --json`。不设置 `--model`，沿用用户默认模型与配置。探针只进行路由加载和必要读取，不运行 App、构建、业务测试、提交、推送或外部发布；它不是完整开发流程验收。提示词中的最多 6 次工具调用是行为约束，进程超时限制另行执行。

输出目录保存 `manifest.json`、`events.jsonl`、`stderr.txt`、`report.json` 和隔离工作区。清单记录实际命令、提示词、runner 源码、案例及 Skill 快照哈希、退出码和超时结果。记录应放在临时目录或所属项目的 `.ios-workflow/evaluations/`，不要加入 Skill、共享模板或案例夹具；工具拒绝把输出放到 Skill 内。原始输出可能含本机路径或项目内容，分享前按实际内容处理。

## 观察与 Token 边界

- 原生适配器读取成功的 `item.completed/command_execution` 事件，支持显式路径的单条 `cat`、`sed`、`head`、`tail`、`nl`、`rg`、`grep` 以及明确成功的 `cd && reader`。只搜索文件名、助手声称已读、运行解释器导入模块均不自动算作向模型加载了规则内容；评测也不能从工具事件观察系统隐式加载。
- Shell 条件分支、多语句、管道、动态展开、递归搜索、失败或无输出的读取、不透明 Python 或未知 MCP/工具事件无法还原读取范围，会使缺失/未加载结论无法判定。仅已观察到的禁止加载和重复读取仍可明确判失败。整体命令返回成功不能证明每个分支实际执行，当前适配器不是完整 Shell 解释器。
- 其他客户端可把**实际文件读取工具事件**转为 `{"type":"module.read","module":"references/standards/tracking-resume.md"}`，保留原始 trace 供追溯。不得把期望列表、模型自述或估算记录转换成实际读取事件。报告将其来源标为 `instrumented`，与原生工具读取区分；工具不能认证导入数据的真实性。
- Token 仅取 `turn.completed.usage` 中实际报告的 `input_tokens`、`cached_input_tokens`、`output_tokens`。已结束轮次分别保留再求和；缓存输入不再次加进输入。如果后续轮次未结束，已报告值仅是已观察轮次小计，`token_status` 标记不完整。缺失或非法值保留 `null`，不使用字符数、词数或上下文长度伪装真实 Token。
- 用量是整个会话报告值，包含系统上下文、其他已安装技能、工具结果与回答，不能直接视为本 Skill 独占成本。比较前后版本须固定案例、模型/客户端配置和运行条件，分别保留快照哈希与缓存情况；单个不同场景的运行不能证明节省比例。

## 验证状态

单元测试用明确标注的合成事件检查解析器、判定逻辑与 CLI 导入；它们不启动真实模型，也不证明模型会正确触发技能。真实前向探针必须另行显式执行并保留其事件和报告。案例已定义、解析器测试通过、真实探针完成和整个矩阵完成是四种不同结论。

开发期间曾使用“换了台电脑”的恢复提示，却只期望恢复模块；该临时 rubric 遗漏了同步模块，应作为旧 rubric 的不可比较样本保留，不能将额外同步读取判成模型缺陷。最终案例已按现有规则拆开同设备与跨设备情形；修改过程中的 Skill 快照也不能当作最终版本后测。

```sh
python3 -m unittest tests.test_module_loading_evaluation -v
```
