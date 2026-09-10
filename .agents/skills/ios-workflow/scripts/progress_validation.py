"""只读检查项目进度的结构、文件引用和证据完整性。

空错误列表只表示这些机械检查通过，不能证明测试确实执行、断言正确或
业务需求已经满足。验收结果、受测环境及未登记的受影响输入仍须按工作流核对。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


STATUSES = frozenset({
    "pending", "in_progress", "implemented", "verified", "blocked", "deferred", "cancelled",
})
EVIDENCE_RESULTS = frozenset({"passed", "failed", "blocked", "skipped"})
VALIDATION_SCOPE = "仅校验结构、路径、证据及已登记输入的完整性；通过不等于业务验收通过。"
SKILL_ROOT = Path(__file__).resolve().parents[1]


def _within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _file(root: Path, value: Any, label: str, errors: list[str], *, evidence: bool = False) -> Path | None:
    """Resolve a portable project-relative file, without allowing directory escapes."""
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: 必须是非空项目相对文件路径")
        return None
    relative = PurePosixPath(value)
    if (relative.is_absolute() or PureWindowsPath(value).drive or "\\" in value
            or ".." in relative.parts or "\x00" in value):
        errors.append(f"{label}: 只允许项目内相对路径，禁止绝对路径、反斜杠和 ..")
        return None
    if evidence and (not relative.parts or relative.parts[0] != ".ios-workflow"):
        errors.append(f"{label}: 证据必须保存在项目 .ios-workflow/ 内")
        return None
    try:
        resolved = (root / value).resolve(strict=True)
        if not _within(resolved, root):
            errors.append(f"{label}: 路径或符号链接越过项目目录")
            return None
        if _within(resolved, SKILL_ROOT):
            errors.append(f"{label}: 不得将工作流 Skill 内容作为项目执行记录或实现")
            return None
        if evidence and not _within(resolved, (root / ".ios-workflow").resolve()):
            errors.append(f"{label}: 证据符号链接越过项目 .ios-workflow/ 目录")
            return None
        if not resolved.is_file():
            errors.append(f"{label}: 必须指向文件")
            return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        errors.append(f"{label}: 文件缺失或路径无法读取")
        return None


def _hash_matches(path: Path | None, expected: Any, label: str, errors: list[str]) -> None:
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        errors.append(f"{label}.sha256: 必须提供 64 位 SHA-256")
        return
    if path is None:
        return
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected.lower():
            errors.append(f"{label}.sha256: 文件已变化，证据不可直接复用")
    except OSError:
        errors.append(f"{label}: 文件无法读取，不能核验证据")


def _valid_recorded_at(value: Any) -> bool:
    """Accept ISO 8601 date-times with an explicit UTC or numeric offset."""
    if not isinstance(value, str) or "T" not in value:
        return False
    # Check the offset separately: fromisoformat normalizes values such as
    # +08:99 instead of rejecting their invalid minute component.
    offset = re.search(r"(?:Z|[+-](?:[01]\d|2[0-3])(?::?[0-5]\d)?)$", value)
    if offset is None:
        return False
    zone = offset.group()
    if zone == "Z":
        zone = "+00:00"
    elif len(zone) == 3:
        zone += ":00"
    elif len(zone) == 5:
        zone = zone[:3] + ":" + zone[3:]
    try:
        parsed = datetime.fromisoformat(value[:offset.start()] + zone)
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def validate_progress(project_root: Path, progress: dict) -> list[str]:
    """Return blocking integrity errors without writing files or updating statuses.

    ``progress`` uses schema_version=1 and an ``items`` list. Each item has a
    stable id, requirement_id, criterion, source {path, section}, status,
    implementation [path], and evidence [{path, sha256, inputs: [{path, sha256}],
    environment, result, recorded_at}]. Each evidence result is passed, failed,
    blocked or skipped, with an ISO 8601 timestamp including a timezone. For a
    verified item, all current evidence must pass, and its inputs collectively
    cover the requirement source and all implementation files. Incomplete
    items may have no evidence. Historical missing fields produce errors;
    this function does not migrate records. Callers must also record affected build
    settings, dependency locks and other inputs; this function cannot infer
    whether the recorded scope is complete or the local environment matches.
    Additional descriptive fields are allowed. Paths use forward slashes
    relative to the business project root.
    """
    errors: list[str] = []
    try:
        root = Path(project_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return ["project_root: 项目目录不存在或无法读取"]
    if not root.is_dir():
        return ["project_root: 必须是项目目录"]
    if _within(root, SKILL_ROOT):
        return ["project_root: 工作流 Skill 及其子目录不能作为业务项目目录"]
    if not isinstance(progress, dict):
        return ["progress: 必须是对象"]
    if type(progress.get("schema_version")) is not int or progress["schema_version"] != 1:
        errors.append("schema_version: 仅支持整数版本 1")
    items = progress.get("items")
    if not isinstance(items, list):
        errors.append("items: 必须是验收项数组")
        return errors

    identifiers: set[str] = set()
    for position, item in enumerate(items):
        label = f"items[{position}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: 必须是验收项对象")
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"{label}.id: 必须是非空稳定 ID")
        elif identifier in identifiers:
            errors.append(f"{label}.id: 重复 ID {identifier}")
        else:
            identifiers.add(identifier)

        for field, description in (("requirement_id", "关联需求 ID"), ("criterion", "可验证的验收条件")):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}.{field}: 待补充非空{description}；不自动迁移历史记录")

        status = item.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{label}.status: 未知状态")
        expected_inputs: set[Path] = set()
        source = item.get("source")
        if not isinstance(source, dict):
            errors.append(f"{label}.source: 必须记录原需求来源 path 和 section")
        else:
            source_path = _file(root, source.get("path"), f"{label}.source.path", errors)
            if source_path:
                expected_inputs.add(source_path)
            if not isinstance(source.get("section"), str) or not source["section"].strip():
                errors.append(f"{label}.source.section: 必须记录需求章节或锚点")

        implementation = item.get("implementation")
        if not isinstance(implementation, list):
            errors.append(f"{label}.implementation: 必须是已有源码或产物路径数组")
        else:
            if status in ("implemented", "verified") and not implementation:
                errors.append(f"{label}.implementation: implemented/verified 必须关联源码或产物")
            for index, path in enumerate(implementation):
                implementation_path = _file(root, path, f"{label}.implementation[{index}]", errors)
                if implementation_path:
                    expected_inputs.add(implementation_path)

        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{label}.evidence: 必须是证据数组")
            continue
        if status == "verified" and not evidence:
            errors.append(f"{label}.evidence: verified 必须有可核对的验证证据")
        recorded_inputs: set[Path] = set()
        for index, entry in enumerate(evidence):
            entry_label = f"{label}.evidence[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{entry_label}: 必须是证据对象")
                continue
            path = _file(root, entry.get("path"), f"{entry_label}.path", errors, evidence=True)
            _hash_matches(path, entry.get("sha256"), entry_label, errors)
            if not isinstance(entry.get("environment"), str) or not entry["environment"].strip():
                errors.append(f"{entry_label}.environment: 待补证，必须记录非空环境说明")
            result = entry.get("result")
            if not isinstance(result, str) or result not in EVIDENCE_RESULTS:
                errors.append(f"{entry_label}.result: 待补证，必须记录 passed/failed/blocked/skipped")
            elif status == "verified" and result != "passed":
                errors.append(f"{entry_label}.result: verified 的当前证据必须为 passed，实际为 {result}")
            if not _valid_recorded_at(entry.get("recorded_at")):
                errors.append(f"{entry_label}.recorded_at: 待补证，必须记录含时区的有效 ISO 8601 时间")
            inputs = entry.get("inputs")
            if not isinstance(inputs, list) or not inputs:
                errors.append(f"{entry_label}.inputs: 必须登记非空受测输入及其 SHA-256")
                continue
            for input_index, input_entry in enumerate(inputs):
                input_label = f"{entry_label}.inputs[{input_index}]"
                if not isinstance(input_entry, dict):
                    errors.append(f"{input_label}: 必须是输入文件对象")
                    continue
                input_path = _file(root, input_entry.get("path"), f"{input_label}.path", errors)
                _hash_matches(input_path, input_entry.get("sha256"), input_label, errors)
                if input_path:
                    recorded_inputs.add(input_path)
        if status == "verified":
            for missing in sorted(expected_inputs - recorded_inputs):
                errors.append(f"{label}.evidence.inputs: 未覆盖需求来源或实现 {missing.relative_to(root)}")
    return errors


def validate_progress_scope(project_root: Path, progress: dict, *, requirement_ids=(), item_ids=()) -> list[str]:
    """仅核对指定需求/验收项的证据，同时保留全账本 ID 唯一性检查。"""
    if not isinstance(progress, dict) or type(progress.get('schema_version')) is not int or progress.get('schema_version') != 1 or not isinstance(progress.get('items'), list):
        return ['progress: 无效账本结构']
    if any(not isinstance(values, (list, tuple)) or not all(isinstance(value, str) and value.strip() for value in values)
           for values in (requirement_ids, item_ids)):
        return ['scope: 必须显式提供需求或验收 ID 数组']
    if not requirement_ids and not item_ids:
        return ['scope: 范围为空；全项目核验请显式调用 validate_progress']
    errors = []
    seen = set()
    selected = []
    found_requirements = set()
    found_items = set()
    for item in progress['items']:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip():
            errors.append('progress: 验收项缺少有效 ID，无法确定范围')
            continue
        if item['id'] in seen:
            errors.append(f"progress: 重复 ID {item['id']}")
        seen.add(item['id'])
        rid = item.get('requirement_id')
        if rid in requirement_ids or item['id'] in item_ids:
            selected.append(item)
            if rid in requirement_ids:
                found_requirements.add(rid)
            found_items.add(item['id'])
    for missing in sorted(set(requirement_ids) - found_requirements):
        errors.append(f'scope: 未找到需求 {missing}')
    for missing in sorted(set(item_ids) - found_items):
        errors.append(f'scope: 未找到验收项 {missing}')
    if errors:
        return errors
    return validate_progress(project_root, {'schema_version': 1, 'items': selected})
