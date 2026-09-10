"""Read-only consistency checks for one requirement's recorded tracking state.

Only tracking JSON and the selected requirement's scalar frontmatter are read.
Matching metadata never proves test execution, business correctness or approval.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from project_generation import ConfigurationError, load_jsonc
from progress_validation import SKILL_ROOT, STATUSES, _file, _within


REQUIREMENT_STATUSES = {"draft", "ready", "in_progress", "blocked", "done", "cancelled"}
MAX_HEADER_BYTES = 65536


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _record(root: Path, path: str, errors: list[str]) -> dict | None:
    resolved = _file(root, path, path, errors, evidence=True)
    if resolved is None:
        return None
    try:
        return load_jsonc(resolved)
    except (ConfigurationError, UnicodeError, RecursionError):
        errors.append(f"{path}: 无法读取有效且嵌套深度受支持的 JSON 对象")
        return None


def _scalar(value: str) -> Any:
    if value == "null":
        return None
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        return int(value)
    if value.startswith('"'):
        parsed = json.loads(value)
        if not isinstance(parsed, str):
            raise ValueError("只支持标量字符串")
        return parsed
    if value.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", value):
            raise ValueError("无效单引号字符串")
        return value[1:-1].replace("''", "'")
    if (not value or value[0] in "[{}]|>&*!%@`" or re.search(r"\s#|:\s", value)
            or value.startswith(("- ", "? "))):
        raise ValueError("不支持嵌套、块值、锚点、标签或未加引号的行内注释")
    return value


def _frontmatter(path: Path, errors: list[str]) -> dict | None:
    """Read at most the opening scalar metadata block, never the Markdown body."""
    fields = {}
    try:
        with path.open("rb") as stream:
            first = stream.readline(MAX_HEADER_BYTES + 1)
            if first.rstrip(b"\r\n") != b"---":
                errors.append("requirement.frontmatter: 缺少开头 ---，不能推断档案元数据")
                return None
            consumed = len(first)
            for number in range(2, 258):
                line = stream.readline(MAX_HEADER_BYTES + 1)
                consumed += len(line)
                if consumed > MAX_HEADER_BYTES:
                    errors.append("requirement.frontmatter: 超过 64 KiB 限制")
                    return None
                text = line.rstrip(b"\r\n").decode("utf-8")
                if text == "---":
                    return fields
                if not line:
                    break
                if not text.strip() or text.lstrip().startswith("#"):
                    continue
                match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)", text)
                if match is None:
                    errors.append(f"requirement.frontmatter:{number}: 只支持平面 key: scalar，请明确处理复杂 YAML")
                    return None
                key, value = match.groups()
                if key in fields:
                    errors.append(f"requirement.frontmatter:{number}: 重复字段 {key}")
                    return None
                try:
                    fields[key] = _scalar(value.strip())
                except (ValueError, RecursionError):
                    errors.append(f"requirement.frontmatter:{number}: {key} 使用了不支持的标量写法")
                    return None
    except (OSError, UnicodeError):
        errors.append("requirement.frontmatter: 文件无法读取")
        return None
    errors.append("requirement.frontmatter: 缺少结束 --- 或超过 256 行限制")
    return None


def _check_tracking_state(root: Path, requirement_id: str | None, index: dict, progress: dict) -> dict:
    """Use already-read snapshots when called by the resume helper."""
    errors: list[str] = []
    result = {"metadata_only": True, "requirement_id": requirement_id,
              "requirement_file": None, "checked": False, "errors": errors}
    if type(index.get("version")) is not int or index.get("version") != 3:
        errors.append("index.version: 仅支持整数版本 3")
    if type(progress.get("schema_version")) is not int or progress.get("schema_version") != 1:
        errors.append("progress.schema_version: 仅支持整数版本 1")
    if "active_requirement" not in index:
        errors.append("index.active_requirement: 缺失，不能判断当前任务")
    active = index.get("active_requirement")
    if active is not None and not isinstance(active, dict):
        errors.append("index.active_requirement: 必须是对象或 null")
        active = None
    if isinstance(active, dict):
        if not _nonempty(active.get("id")):
            errors.append("index.active_requirement.id: 必须是非空稳定 ID")
        if active.get("status") in ("done", "cancelled"):
            errors.append("index.active_requirement: done/cancelled 需求应清空活动索引")
        if requirement_id is None and _nonempty(active.get("id")):
            requirement_id = active["id"]
    if requirement_id is not None and (not _nonempty(requirement_id) or len(requirement_id) > 256):
        errors.append("requirement_id: 必须是长度不超过 256 的非空稳定 ID")
        return result
    result["requirement_id"] = requirement_id
    if requirement_id is None or errors:
        return result
    selected = []
    items = progress.get("items")
    if not isinstance(items, list):
        errors.append("progress.items: 必须是验收项数组")
        return result
    identifiers = set()
    for position, item in enumerate(items):
        if (not isinstance(item, dict) or not _nonempty(item.get("id"))
                or not _nonempty(item.get("requirement_id"))):
            errors.append(f"progress.items[{position}]: 缺少有效 ID 或需求关联，无法确定范围")
            continue
        if item["id"] in identifiers:
            errors.append(f"progress.items[{position}]: 重复验收 ID")
        identifiers.add(item["id"])
        if item["requirement_id"] == requirement_id:
            selected.append(item)
    if not selected:
        errors.append("progress.items: 没有选定需求的验收项，不能判断状态一致性")

    history = _record(root, ".ios-workflow/history.jsonc", errors)
    row = None
    if history is not None:
        if type(history.get("version")) is not int or history.get("version") != 3 or history.get("project") != ".":
            errors.append("history: 需要 version=3 且 project=. 的项目内台账")
        order = history.get("execution_order")
        sequences = set()
        requirements = set()
        if not isinstance(order, list):
            errors.append("history.execution_order: 必须是数组")
        else:
            for position, entry in enumerate(order):
                label = f"history.execution_order[{position}]"
                if not isinstance(entry, dict) or not _nonempty(entry.get("id")):
                    errors.append(f"{label}: 缺少有效需求 ID")
                    continue
                if entry["id"] in requirements:
                    errors.append(f"{label}: 重复需求 ID")
                requirements.add(entry["id"])
                sequence = entry.get("sequence")
                if type(sequence) is not int or sequence < 1:
                    errors.append(f"{label}.sequence: 必须是正整数")
                elif sequence in sequences:
                    errors.append(f"{label}.sequence: 重复执行序号")
                else:
                    sequences.add(sequence)
                if not isinstance(entry.get("status"), str) or entry["status"] not in REQUIREMENT_STATUSES:
                    errors.append(f"{label}.status: 未知需求状态")
                if entry.get("project", ".") != ".":
                    errors.append(f"{label}.project: 必须是当前业务项目 .")
                if not _nonempty(entry.get("file")):
                    errors.append(f"{label}.file: 缺少档案相对路径")
                if entry["id"] == requirement_id:
                    row = entry
        next_sequence = history.get("next_sequence")
        if type(next_sequence) is not int or next_sequence < 1 or next_sequence <= max(sequences, default=0):
            errors.append("history.next_sequence: 必须是大于所有已登记序号的正整数")

    selected_active = active if isinstance(active, dict) and active.get("id") == requirement_id else None
    reference = selected_active.get("file") if selected_active else row.get("file") if row else f".ios-workflow/requirements/{requirement_id}.md"
    archive = _file(root, reference, "requirement.file", errors, evidence=True)
    if archive is None:
        return result
    result["requirement_file"] = reference
    fields = _frontmatter(archive, errors)
    if fields is None:
        return result
    result["checked"] = True
    if fields.get("id") != requirement_id:
        errors.append("requirement.id: 档案 ID 与选定需求不一致")
    if fields.get("project") != ".":
        errors.append("requirement.project: 档案必须属于当前业务项目 .")
    status = fields.get("status")
    if not isinstance(status, str) or status not in REQUIREMENT_STATUSES:
        errors.append("requirement.status: 缺失或未知需求状态")
    sequence = fields.get("sequence")
    if "sequence" not in fields or (sequence is not None and (type(sequence) is not int or sequence < 1)):
        errors.append("requirement.sequence: 必须是 null 或正整数")
    if status in ("in_progress", "blocked", "done") and (type(sequence) is not int or sequence < 1):
        errors.append("requirement.sequence: 已执行需求必须记录正整数执行序号")
    if row is None and (type(sequence) is int or status in ("in_progress", "blocked", "done")):
        errors.append("history.execution_order: 已执行的选定需求缺少台账记录")
    if row is not None:
        for key in ("sequence", "status"):
            if fields.get(key) != row.get(key):
                errors.append(f"requirement.{key}: 档案与执行台账不一致")
        history_file = _file(root, row.get("file"), "history.requirement.file", errors, evidence=True)
        if history_file is not None and history_file != archive:
            errors.append("requirement.file: 活动索引与执行台账指向不同档案")
    if selected_active:
        for key in ("status", "project"):
            if fields.get(key) != selected_active.get(key):
                errors.append(f"requirement.{key}: 档案与活动索引不一致")
        # Older templates keep the step only in the Markdown body. Do not
        # require migration or scan the body merely to compare a summary.
        if "current_step" in fields and fields["current_step"] != selected_active.get("current_step"):
            errors.append("requirement.current_step: 已记录的档案步骤与活动索引不一致")
    for item in selected:
        item_status = item.get("status")
        if not isinstance(item_status, str) or item_status not in STATUSES:
            errors.append(f"progress.{item['id']}.status: 未知验收状态")
            continue
        if status == "done" and item_status not in ("verified", "deferred", "cancelled"):
            errors.append(f"progress.{item['id']}: 需求为 done，但验收仍为 {item_status}")
        if status == "done" and item_status == "verified":
            evidence = item.get("evidence")
            if (not isinstance(evidence, list) or not evidence
                    or any(not isinstance(entry, dict) or entry.get("result") != "passed" for entry in evidence)):
                errors.append(f"progress.{item['id']}: done 的 verified 验收缺少登记的成功证据")
        if item_status in ("deferred", "cancelled"):
            decision = item.get("scope_decision")
            if not isinstance(decision, dict) or not _nonempty(decision.get("reason")):
                errors.append(f"progress.{item['id']}.scope_decision: 延期/取消缺少决定理由与来源")
                continue
            source = decision.get("source")
            if not isinstance(source, dict) or not _nonempty(source.get("section")):
                errors.append(f"progress.{item['id']}.scope_decision.source: 必须记录来源 path 和 section")
            else:
                _file(root, source.get("path"), f"progress.{item['id']}.scope_decision.source.path", errors)
    return result


def validate_tracking_state(project_root: Path, requirement_id: str | None = None) -> dict:
    """Check selected metadata links, without reading reports or marking done."""
    errors: list[str] = []
    result = {"metadata_only": True, "requirement_id": requirement_id,
              "requirement_file": None, "checked": False, "errors": errors}
    try:
        root = Path(project_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        errors.append("project_root: 项目目录不存在或无法读取")
        return result
    if not root.is_dir() or _within(root, SKILL_ROOT):
        errors.append("project_root: 必须是 Skill 之外的业务项目目录")
        return result
    index = _record(root, ".ios-workflow/index.jsonc", errors)
    progress = _record(root, ".ios-workflow/progress.json", errors)
    if index is None or progress is None:
        return result
    return _check_tracking_state(root, requirement_id, index, progress)
