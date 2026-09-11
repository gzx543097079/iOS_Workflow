"""Small JSON CLI over the existing project tracking and evidence interfaces.

The client must invoke these commands at its own phase boundaries. This module
does not intercept editor writes, execute tests or infer business acceptance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import tracking_update
from evidence_tools import capture_evidence, compare_evidence
from project_generation import strip_jsonc
from requirement_gate import assess_requirement_gate
from resume_context import load_resume_context


REQUEST_COMMANDS = {"gate", "prepare", "capture", "compare"}
TRANSACTION_COMMANDS = {
    "apply": tracking_update.apply_tracking_update,
    "recover": tracking_update.recover_tracking_update,
    "abandon": tracking_update.abandon_tracking_update,
}


def _record_path(value):
    path = tracking_update._path(value)
    if not path.startswith(".ios-workflow/"):
        raise ValueError("请求与证据记录必须保存在业务项目 .ios-workflow/ 内")
    return path


def read_request(root: Path, relative: str) -> dict:
    """Read local JSONC without echoing its content or following symlinks."""
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("JSON 存在重复字段")
            value[key] = item
        return value

    def invalid_constant(_):
        raise ValueError("JSON 不支持非有限数值")

    try:
        content = tracking_update._read(root, _record_path(relative)).decode("utf-8")
        value = json.loads(strip_jsonc(content), object_pairs_hook=unique_object,
                           parse_constant=invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError("请求或证据记录无法读取为有效 JSONC 对象；检查文件路径、编码与字段") from error
    if not isinstance(value, dict):
        raise ValueError("请求或证据记录必须是 JSON 对象")
    return value


def _fields(request, required, optional=()):
    if not isinstance(request, dict):
        raise ValueError("本命令需要请求对象")
    missing = set(required) - set(request)
    unknown = set(request) - set(required) - set(optional)
    if missing or unknown:
        # Do not repeat untrusted values (or arbitrarily long field names).
        raise ValueError("请求字段不符合命令契约；检查必需字段及多余字段")


def _diagnostics(values):
    return [str(value)[:400] for value in values[:10]]


def run_command(command, project_root, request=None, *, requirement_id=None,
                max_items=20, offset=0, transaction_id=None, output=None) -> dict:
    """Return a versioned response; callers use ``ok`` or the CLI exit status.

    Requests are kept local. ``capture`` writes a new evidence metadata file and
    returns its location; it never overwrites a prior record or promotes status.
    Additional operations should compose existing validation/transaction APIs.
    """
    response = {"schema_version": 1, "command": command, "ok": False,
                "result": None, "errors": [], "error_count": 0}
    try:
        root = tracking_update._root(project_root)
        errors = []
        if command == "gate":
            _fields(request, ("task_kind", "phase", "card"), (
                "requirement_id", "low_risk", "single_turn", "acceptance_clear",
                "continuity_required", "related_requirement"))
            result = assess_requirement_gate(root, **request)
            errors = result.pop("errors")
            ok = result["gate_passed"]
        elif command == "resume":
            result = load_resume_context(root, requirement_id, max_items, offset)
            errors = result.pop("errors")
            ok = not result["error_count"]
        elif command == "prepare":
            _fields(request, ("requirement_id", "candidates", "expected_hashes"))
            identifier = tracking_update.prepare_tracking_update(root, **request)
            result = {"transaction_id": identifier, "state": "prepared", "metadata_only": True}
            ok = True
        elif command in TRANSACTION_COMMANDS:
            result = TRANSACTION_COMMANDS[command](root, transaction_id)
            ok = True
        elif command == "capture":
            _fields(request, ("evidence_path", "input_paths", "environment", "result"), ("recorded_at",))
            path = _record_path(output)
            if not path.startswith(".ios-workflow/evidence-records/") or not path.endswith(".json"):
                raise ValueError("capture --output 必须是 .ios-workflow/evidence-records/ 内的新 JSON 文件")
            record = capture_evidence(root, **request)
            content = (json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
            tracking_update._write(root, path, content)
            result = {"record_path": path, "evidence_path": record["path"],
                      "result": record["result"], "input_count": len(record["inputs"]),
                      "recorded_at": record["recorded_at"], "metadata_only": True}
            ok = True
        elif command == "compare":
            _fields(request, ("record_path", "current_environment", "current_input_paths"))
            record = read_request(root, request["record_path"])
            result = compare_evidence(root, record, request["current_environment"], request["current_input_paths"])
            errors = result.pop("reasons")
            ok = result["status"] == "matched"
        else:
            raise ValueError("未知命令")
        response.update(ok=ok, result=result, errors=_diagnostics(errors),
                        error_count=max(len(errors), result.get("error_count", 0)))
    except (OSError, ValueError, TypeError, RecursionError) as error:
        response.update(errors=_diagnostics([error]), error_count=1)
    return response


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # A parse failure is also machine-readable; never echo argument values.
        raise ValueError("命令参数无效；运行 --help 查看用法")


def main(argv=None) -> int:
    parser = _Parser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in sorted(REQUEST_COMMANDS | set(TRANSACTION_COMMANDS) | {"resume"}):
        command = subparsers.add_parser(name)
        command.add_argument("--project-root", required=True, type=Path)
        if name in REQUEST_COMMANDS:
            command.add_argument("--request", required=True, help="项目 .ios-workflow/ 内的相对 JSONC 路径")
        if name in TRANSACTION_COMMANDS:
            command.add_argument("--transaction-id", required=True)
        if name == "resume":
            command.add_argument("--requirement-id")
            command.add_argument("--max-items", type=int, default=20)
            command.add_argument("--offset", type=int, default=0)
        if name == "capture":
            command.add_argument("--output", required=True, help="新的 .ios-workflow/evidence-records/*.json 路径")
    command_name = None
    try:
        arguments = vars(parser.parse_args(argv))
        command_name = arguments.pop("command")
        project_root = arguments.pop("project_root")
        request_path = arguments.pop("request", None)
        request = read_request(tracking_update._root(project_root), request_path) if request_path else None
        response = run_command(command_name, project_root, request, **arguments)
    except (OSError, ValueError, TypeError, RecursionError) as error:
        response = {"schema_version": 1, "command": command_name, "ok": False,
                    "result": None, "errors": _diagnostics([error]), "error_count": 1}
    print(json.dumps(response, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
