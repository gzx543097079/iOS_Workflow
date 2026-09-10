"""Evaluate observed Skill reads and reported usage; never infer them from prompts.

This maintenance tool is deliberately outside the distributed Skill. Native
Codex exec JSONL and explicit instrumented module.read events are supported.
Opaque tools/commands make absence checks inconclusive instead of passing.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RUNNER_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
CASES = ROOT / "tests/fixtures/module-loading-cases.json"
SKILL_RELATIVE = ".agents/skills/ios-workflow"
READERS = {"cat", "head", "tail", "sed", "rg", "grep", "nl"}
METADATA_COMMANDS = {"pwd", "ls", "stat", "true", "false", "wc", "sha256sum", "shasum"}
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")


def load_case(case_id: str, cases_path: Path = CASES) -> dict:
    corpus = json.loads(cases_path.read_text(encoding="utf-8"))
    matches = [case for case in corpus["cases"] if case["id"] == case_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one case named {case_id}")
    return matches[0]


def _module(path: str, cwd: Path, skill_root: Path) -> str | None:
    target = Path(path) if Path(path).is_absolute() else cwd / path
    try:
        return target.resolve().relative_to(skill_root.resolve()).as_posix()
    except ValueError:
        return None


def validate_output_location(output: Path, skill_root: Path | None = None) -> None:
    protected = [ROOT / SKILL_RELATIVE]
    if skill_root is not None:
        protected.append(skill_root)
    if any(output.resolve().is_relative_to(root.resolve()) for root in protected):
        raise ValueError("Evaluation records must remain outside the distributed Skill")


def command_reads(command: str, project_root: Path, skill_root: Path) -> tuple[list[str], list[str]]:
    """Parse a bounded shell subset, never execute commands or guess expansions."""
    try:
        outer = shlex.split(command)
        if outer and Path(outer[0]).name in {"sh", "bash", "zsh"}:
            option = next((i for i, value in enumerate(outer) if value in {"-c", "-lc"}), None)
            if option is None or option + 2 != len(outer):
                return [], [command]
            command = outer[option + 1]
        if re.search(r"\$|`|<<|<\(|>\(|\n", command):
            return [], [command]
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        return [], [command]
    # An aggregate exit code cannot prove that conditional branches or earlier
    # statements ran successfully, or that a pipeline exposed module contents.
    if any(word in {";", "||", "|", "&", "(", ")", "<", ">", ">>"} for word in words):
        return [], [command]
    if "&&" in words and (words.count("&&") != 1 or words.index("&&") != 2
                           or words[0] != "cd" or len(words) < 4 or Path(words[3]).name not in READERS):
        return [], [command]
    segments: list[list[str]] = [[]]
    for word in words:
        if word in {";", "&&", "||", "|"}:
            segments.append([])
        else:
            segments[-1].append(word)
    reads, unknown = [], []
    cwd = project_root
    for segment in segments:
        if not segment:
            continue
        executable, arguments = Path(segment[0]).name, segment[1:]
        if executable == "cd" and len(arguments) == 1:
            cwd = Path(arguments[0]) if Path(arguments[0]).is_absolute() else cwd / arguments[0]
            continue
        if executable in METADATA_COMMANDS or (executable == "rg" and "--files" in arguments):
            continue
        if executable == "git" and arguments and arguments[0] in {"status", "rev-parse", "branch", "remote", "rev-list"}:
            continue
        if executable == "find" and not any(value in {"-exec", "-execdir", "-ok", "-okdir"} for value in arguments):
            continue
        if executable in {"echo", "printf"}:
            continue
        if executable not in READERS or any(value in {"<", ">", ">>", "(", ")"} for value in arguments):
            unknown.append(shlex.join(segment))
            continue
        if executable in {"rg", "grep"} and any(
                value.split("=", 1)[0] in {"--files-with-matches", "--files-without-match", "--count", "--count-matches", "--quiet"}
                or re.match(r"^-[A-Za-z]*[lcLq]", value) for value in arguments):
            unknown.append(shlex.join(segment))
            continue
        # Options with separate operands and reader expressions are not files.
        files, skip_next = [], False
        expression_pending = executable in {"sed", "rg", "grep"}
        for argument in arguments:
            if skip_next:
                skip_next = False
                continue
            if argument in {"-e", "--regexp"}:
                expression_pending = False
                skip_next = True
                continue
            if argument in {"-n", "-c"} and executable in {"head", "tail"}:
                skip_next = True
                continue
            if argument in {"-A", "-B", "-C", "-m", "--glob", "-g"}:
                skip_next = True
                continue
            if argument.startswith("-"):
                continue
            if expression_pending:
                expression_pending = False
                continue
            files.append(argument)
        for path in files:
            if any(character in path for character in "*?["):
                unknown.append(shlex.join(segment))
                continue
            target = Path(path) if Path(path).is_absolute() else cwd / path
            if executable in {"rg", "grep"} and (target.is_dir() or not Path(path).suffix):
                unknown.append(shlex.join(segment))
                continue
            module = _module(path, cwd, skill_root)
            if module:
                reads.append(module)
        if executable in {"rg", "grep"} and not files:
            unknown.append(shlex.join(segment))
    return reads, unknown


def parse_trace(trace_path: Path, project_root: Path, skill_root: Path | None = None) -> dict:
    skill_root = skill_root or project_root / SKILL_RELATIVE
    reads, unknown, usage, errors = [], [], [], []
    completed, failed, turn_ended = False, False, False
    seen_items: set[str] = set()
    for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {line_number}: invalid JSON")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {line_number}: event must be an object")
            continue
        event_type = event.get("type")
        if event_type == "turn.started":
            seen_items.clear()
            turn_ended = False
            completed = False
        elif event_type == "turn.completed":
            if turn_ended:
                errors.append(f"line {line_number}: duplicate turn completion without turn.started")
                continue
            turn_ended = True
            completed = True
            raw = event.get("usage")
            if isinstance(raw, dict):
                usage.append({key: value if type(value := raw.get(key)) is int and value >= 0 else None
                              for key in TOKEN_FIELDS})
            else:
                usage.append(dict.fromkeys(TOKEN_FIELDS))
        elif event_type in {"turn.failed", "error"}:
            failed = True
        elif event_type == "module.read":
            module = event.get("module")
            if (not isinstance(module, str) or not module or "\\" in module
                    or Path(module).is_absolute() or ".." in Path(module).parts):
                errors.append(f"line {line_number}: invalid instrumented module path")
            else:
                reads.append({"module": module, "event": line_number, "source": "instrumented"})
        elif event_type == "item.completed":
            item = event.get("item")
            if not isinstance(item, dict):
                errors.append(f"line {line_number}: missing item")
                continue
            identifier = item.get("id")
            if identifier is not None:
                if str(identifier) in seen_items:
                    continue
                seen_items.add(str(identifier))
            if item.get("type") == "command_execution":
                command = item.get("command")
                if not isinstance(command, str):
                    unknown.append(f"line {line_number}: command unavailable")
                elif item.get("exit_code") != 0:
                    unknown.append(f"line {line_number}: command failed; partial reads cannot be inferred")
                else:
                    modules, opaque = command_reads(command, project_root, skill_root)
                    if modules and not item.get("aggregated_output"):
                        unknown.append(f"line {line_number}: read returned no observable content")
                    else:
                        reads.extend({"module": module, "event": line_number, "source": "executed_shell_read"} for module in modules)
                    unknown.extend(f"line {line_number}: {command}" for command in opaque)
            elif item.get("type") not in {"agent_message", "reasoning", "todo_list"}:
                unknown.append(f"line {line_number}: unsupported tool event {item.get('type')}")
        elif event_type not in {"thread.started", "item.started", "item.updated"}:
            unknown.append(f"line {line_number}: unsupported event {event_type}")
    totals = {key: sum(turn[key] for turn in usage) if usage and all(turn[key] is not None for turn in usage) else None
              for key in TOKEN_FIELDS}
    return {"reads": reads, "unobserved_actions": unknown, "parse_errors": errors,
            "completed": completed and not failed, "usage": totals, "turn_usage": usage,
            "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            "observation_scope": "Executed shell read events and explicit instrumented reads; model prose and filename listings are not reads."}


def evaluate(case: dict, actual: dict) -> dict:
    counts = Counter(read["module"] for read in actual["reads"])
    matches = lambda patterns, module: any(fnmatch.fnmatchcase(module, pattern) for pattern in patterns)
    missing = [pattern for pattern in case["expected_modules"] if not any(fnmatch.fnmatchcase(module, pattern) for module in counts)]
    forbidden = sorted(module for module in counts if matches(case["forbidden_modules"], module))
    unexpected = sorted(module for module in counts if not matches(case["expected_modules"] + case["optional_modules"], module))
    repeated = {module: count for module, count in sorted(counts.items()) if count > case["max_reads_per_module"]}
    conclusive = actual["completed"] and not actual["unobserved_actions"] and not actual["parse_errors"]
    status = "fail" if forbidden or unexpected or repeated or (conclusive and missing) else ("pass" if conclusive else "inconclusive")
    return {"case_id": case["id"], "status": status,
            "case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
            "expected": {key: case[key] for key in ("expected_modules", "optional_modules", "forbidden_modules", "max_reads_per_module")},
            "actual": actual, "loaded_modules": sorted(counts), "read_counts": dict(sorted(counts.items())),
            "missing_expected": missing, "forbidden_loaded": forbidden, "unexpected_loaded": unexpected, "repeated_reads": repeated,
            "token_status": "reported" if actual["completed"] and not actual["parse_errors"] and all(actual["usage"][key] is not None for key in TOKEN_FIELDS) else "unavailable_or_partial",
            "limitations": "Usage is the complete Codex turn usage, including existing context; it is not Skill-only cost or a measured saving. A read-only probe does not validate development or delivery."}


def run_case(case: dict, output: Path, timeout: int = 120, codex: str = "codex") -> dict:
    """Run one opt-in read-only forward probe, keeping the user's default model."""
    validate_output_location(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite evaluation output: {output}")
    executable = shutil.which(codex)
    if not executable:
        raise FileNotFoundError(f"Codex CLI unavailable: {codex}")
    output.mkdir(parents=True)
    workspace = output / "workspace"
    workspace.mkdir()
    shutil.copytree(ROOT / SKILL_RELATIVE, workspace / SKILL_RELATIVE,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(ROOT / "distribution/project.example.jsonc", workspace / "project.example.jsonc")
    for relative, content in case["files"].items():
        target = workspace / relative
        if target.resolve().is_relative_to(workspace.resolve()) is False:
            raise ValueError(f"Fixture path escapes workspace: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    prompt = case["prompt"] + "\n\n本轮是只读前向评测：只执行适用规则加载与必要读取，至多 6 次工具调用。不修改文件，不运行构建或测试，不执行提交、推送、发布，不联网或操作外部应用。说明当前登记事实与下一步；不要把评测夹具当作真实验收证据。"
    command = [executable, "-a", "never", "exec", "--sandbox", "read-only", "--skip-git-repo-check",
               "--ephemeral", "--json", "-C", str(workspace), "-"]
    manifest = {"case_id": case["id"], "case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
                "runner_sha256": RUNNER_SOURCE_SHA256,
                "started_at": datetime.now(timezone.utc).isoformat(), "command": command, "prompt": prompt,
                "project_root": str(workspace), "model_override": None, "exit_code": None, "timed_out": False}
    skill_files = {path.relative_to(workspace / SKILL_RELATIVE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted((workspace / SKILL_RELATIVE).rglob("*")) if path.is_file()}
    manifest["skill_snapshot_sha256"] = hashlib.sha256(json.dumps(skill_files, sort_keys=True).encode()).hexdigest()
    trace = output / "events.jsonl"
    with trace.open("w", encoding="utf-8") as stdout, (output / "stderr.txt").open("w", encoding="utf-8") as stderr:
        try:
            result = subprocess.run(command, input=prompt, text=True, stdout=stdout, stderr=stderr, timeout=timeout)
            manifest["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            manifest["timed_out"] = True
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    actual = parse_trace(trace, workspace)
    if manifest["timed_out"] or manifest["exit_code"] != 0:
        actual["completed"] = False
    report = evaluate(case, actual)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="operation", required=True)
    imported = subcommands.add_parser("evaluate", help="Evaluate actual JSONL events; never launch a model")
    imported.add_argument("--case", required=True)
    imported.add_argument("--trace", type=Path, required=True)
    imported.add_argument("--project-root", type=Path, required=True)
    imported.add_argument("--skill-root", type=Path)
    imported.add_argument("--output", type=Path)
    forward = subcommands.add_parser("run", help="Opt in to one real Codex session using the default model")
    forward.add_argument("--case", required=True)
    forward.add_argument("--output", type=Path, required=True)
    forward.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    case = load_case(args.case)
    if args.operation == "run":
        report = run_case(case, args.output.resolve(), timeout=args.timeout)
    else:
        report = evaluate(case, parse_trace(args.trace, args.project_root, args.skill_root))
        if args.output:
            validate_output_location(args.output, args.skill_root or args.project_root / SKILL_RELATIVE)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"case_id": report["case_id"], "status": report["status"], "usage": report["actual"]["usage"],
                      "loaded_modules": report["loaded_modules"], "missing_expected": report["missing_expected"],
                      "forbidden_loaded": report["forbidden_loaded"], "repeated_reads": report["repeated_reads"],
                      "unexpected_loaded": report["unexpected_loaded"], "token_status": report["token_status"],
                      "unobserved_actions": len(report["actual"]["unobserved_actions"])}, ensure_ascii=False))
    return 0 if report["status"] == "pass" else (1 if report["status"] == "fail" else 2)


if __name__ == "__main__":
    sys.exit(main())
