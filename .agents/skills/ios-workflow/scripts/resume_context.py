"""只读提取项目恢复摘要；记录状态不等于当前已验证状态。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from project_generation import ConfigurationError, load_jsonc
from progress_validation import SKILL_ROOT, STATUSES, _file, _within
from tracking_state import _check_tracking_state


CONTEXT_SCOPE = "提取当前页元数据并核对选定需求的记录一致性；未核验证据内容、哈希、环境或业务验收，不作完成判断。"
_REQUIREMENT_STATUSES = {"draft", "ready", "in_progress", "blocked", "done", "cancelled"}


class _BoundedList(list):
    """Keep diagnostics compact while retaining the true omitted count."""

    def __init__(self, limit: int):
        super().__init__()
        self.limit = limit
        self.total_count = 0

    def append(self, value):
        self.total_count += 1
        if len(self) < self.limit:
            super().append(value)


def _finish(result: dict) -> dict:
    for field in ("errors", "truncated_fields"):
        values = result[field]
        result["omitted"][field] = values.total_count - len(values)
        result[field] = list(values)
    result["error_count"] = len(result["errors"]) + result["omitted"]["errors"]
    result["truncated"] = bool(result["truncated_fields"] or any(result["omitted"].values()))
    return result


def _reference(root: Path, value: Any, label: str, errors: list[str], *, evidence: bool = False) -> Path | None:
    if isinstance(value, str) and len(value) > 1024:
        errors.append(f"{label}: 路径超过 1024 字符，未输出或截断路径")
        return None
    return _file(root, value, label, errors, evidence=evidence)


def _read_record(root: Path, relative: str, errors: list[str]) -> dict | None:
    path = _reference(root, relative, relative, errors, evidence=True)
    if path is None:
        return None
    try:
        return load_jsonc(path)
    except (ConfigurationError, UnicodeError, RecursionError):
        errors.append(f"{relative}: 无法读取有效 JSON 对象")
        return None


def _text(value: Any, label: str, errors: list[str], *, empty: bool = False,
          limit: int = 800, truncated_fields: list[str] | None = None) -> str | None:
    if not isinstance(value, str) or (not empty and not value.strip()):
        errors.append(f"{label}: 必须是{'字符串' if empty else '非空字符串'}")
        return None
    if len(value) > limit:
        if truncated_fields is None:
            errors.append(f"{label}: 超过 {limit} 字符，未输出或截断标识")
            return None
        truncated_fields.append(label)
        return value[:limit - 1] + "…"
    return value


def load_resume_context(project_root: Path, requirement_id: str | None = None,
                        max_items: int = 20, offset: int = 0) -> dict:
    """Return a bounded page of recorded metadata, without changing any files.

    With no explicit ID, only ``index.active_requirement`` selects work; an
    empty active index does not imply that every requirement is complete.
    ``recorded_status`` deliberately preserves that distinction. The caller
    must validate the selected requirement's evidence before reusing it.
    Read index/progress JSON, history linkage metadata and only the selected
    requirement's scalar frontmatter. Markdown bodies, handoff text, evidence
    contents, historical generation configuration and unrelated archives are not.
    ``required_files`` lists safe project-relative entry points for follow-up.
    Summary text is capped at 800 characters, blockers at 20 and diagnostics
    at 50. ``truncated_fields`` and ``omitted`` disclose shortened output;
    IDs over 256 or paths over 1024 characters are rejected, never shortened.
    """
    errors = _BoundedList(50)
    truncated_fields = _BoundedList(50)
    result = {
        "metadata_only": True, "validation_scope": CONTEXT_SCOPE,
        "tracking_state_checked": False,
        "requirement_id": None, "active_requirement": None, "items": [],
        "blockers": [], "next_action": None, "required_files": [],
        "total_items": 0, "offset": offset, "max_items": max_items,
        "has_more": False, "errors": errors, "truncated_fields": truncated_fields,
        "omitted": {"blockers": 0},
    }
    if type(max_items) is not int or not 1 <= max_items <= 100:
        errors.append("max_items: 必须是 1 到 100 的整数")
        result["max_items"] = None
    if type(offset) is not int or offset < 0:
        errors.append("offset: 必须是非负整数")
        result["offset"] = None
    if requirement_id is not None and _text(requirement_id, "requirement_id", errors, limit=256) is None:
        return _finish(result)
    if errors:
        return _finish(result)
    try:
        root = Path(project_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        errors.append("project_root: 项目目录不存在或无法读取")
        return _finish(result)
    if not root.is_dir() or _within(root, SKILL_ROOT):
        errors.append("project_root: 必须是工作流 Skill 之外的业务项目目录")
        return _finish(result)

    required_files: set[str] = set()
    index_path = ".ios-workflow/index.jsonc"
    progress_path = ".ios-workflow/progress.json"
    index = _read_record(root, index_path, errors)
    progress = _read_record(root, progress_path, errors)
    if index is not None:
        required_files.add(index_path)
    if progress is not None:
        required_files.add(progress_path)
    active = None
    if index is not None:
        if type(index.get("version")) is not int or index["version"] != 3:
            errors.append("index.version: 仅支持整数版本 3")
        elif "active_requirement" not in index:
            errors.append("index.active_requirement: 字段缺失，不能推断当前任务")
        elif index["active_requirement"] is not None:
            if isinstance(index["active_requirement"], dict):
                active = index["active_requirement"]
                active_id = _text(active.get("id"), "index.active_requirement.id", errors, limit=256)
                if requirement_id is None:
                    requirement_id = active_id
            else:
                errors.append("index.active_requirement: 必须是对象或 null")
    result["requirement_id"] = requirement_id
    if active is not None and active.get("id") == requirement_id:
        summary = {"id": requirement_id}
        for field in ("title", "evidence_key", "branch", "observed_head", "updated_at"):
            summary[field] = _text(active.get(field), f"index.active_requirement.{field}", errors,
                                   empty=True, truncated_fields=truncated_fields)
        summary["current_step"] = _text(active.get("current_step"), "index.active_requirement.current_step",
                                         errors, empty=True, limit=256)
        scope_version = active.get("scope_version")
        if type(scope_version) is not int or scope_version < 1:
            errors.append("index.active_requirement.scope_version: 必须是正整数")
            scope_version = None
        summary["scope_version"] = scope_version
        if active.get("project") != ".":
            errors.append("index.active_requirement.project: 必须是当前业务项目 .")
        status = active.get("status")
        if not isinstance(status, str) or status not in _REQUIREMENT_STATUSES:
            errors.append("index.active_requirement.status: 未知状态")
            status = None
        summary["recorded_status"] = status
        file = active.get("file")
        if _reference(root, file, "index.active_requirement.file", errors, evidence=True):
            summary["file"] = file
            required_files.add(file)
        result["next_action"] = _text(active.get("next_action"), "index.active_requirement.next_action",
                                       errors, empty=True, truncated_fields=truncated_fields)
        blockers = active.get("blockers")
        if isinstance(blockers, list) and all(isinstance(v, str) and v.strip() for v in blockers):
            result["blockers"] = [_text(value, f"index.active_requirement.blockers[{number}]", errors,
                                        truncated_fields=truncated_fields)
                                  for number, value in enumerate(blockers[:20])]
            result["omitted"]["blockers"] = max(len(blockers) - 20, 0)
        else:
            errors.append("index.active_requirement.blockers: 必须是非空字符串组成的数组")
        result["active_requirement"] = summary

    handoff = ".ios-workflow/handoff.md"
    if (root / handoff).exists() or (root / handoff).is_symlink():
        if _reference(root, handoff, handoff, errors, evidence=True):
            required_files.add(handoff)
    if progress is not None:
        if type(progress.get("schema_version")) is not int or progress["schema_version"] != 1:
            errors.append("progress.schema_version: 仅支持整数版本 1")
        elif not isinstance(progress.get("items"), list):
            errors.append("progress.items: 必须是验收项数组")
        else:
            identifiers: set[str] = set()
            selected = []
            for position, item in enumerate(progress["items"]):
                label = f"progress.items[{position}]"
                if not isinstance(item, dict):
                    errors.append(f"{label}: 必须是验收项对象")
                    continue
                identifier = _text(item.get("id"), f"{label}.id", errors, limit=256)
                if identifier in identifiers:
                    errors.append(f"{label}.id: 重复验收 ID，需核对账本")
                if identifier is not None:
                    identifiers.add(identifier)
                item_requirement = _text(item.get("requirement_id"), f"{label}.requirement_id", errors, limit=256)
                if requirement_id is not None and item_requirement == requirement_id:
                    selected.append((label, item, identifier))
            result["total_items"] = len(selected)
            result["has_more"] = offset + max_items < len(selected)
            if requirement_id is not None and not selected:
                errors.append("requirement_id: 账本中没有该需求的验收项，不能判断进度")
            for label, item, identifier in selected[offset:offset + max_items]:
                summary = {"id": identifier, "requirement_id": requirement_id}
                summary["criterion"] = _text(item.get("criterion"), f"{label}.criterion", errors,
                                              truncated_fields=truncated_fields)
                status = item.get("status")
                if not isinstance(status, str) or status not in STATUSES:
                    errors.append(f"{label}.status: 未知状态")
                    status = None
                summary["recorded_status"] = status
                source = item.get("source")
                if not isinstance(source, dict):
                    errors.append(f"{label}.source: 必须是来源对象")
                else:
                    section = _text(source.get("section"), f"{label}.source.section", errors,
                                    truncated_fields=truncated_fields)
                    if _reference(root, source.get("path"), f"{label}.source.path", errors):
                        summary["source"] = {"path": source["path"], "section": section}
                for field in ("implementation", "evidence"):
                    entries = item.get(field)
                    if not isinstance(entries, list):
                        errors.append(f"{label}.{field}: 必须是数组")
                        summary[f"{field}_count"] = None
                        continue
                    summary[f"{field}_count"] = len(entries)
                    if not entries and (status == "verified" or field == "implementation" and status == "implemented"):
                        errors.append(f"{label}.{field}: 已记录状态缺少关联文件，须重新核验")
                    for number, entry in enumerate(entries):
                        reference = entry if field == "implementation" else entry.get("path") if isinstance(entry, dict) else None
                        _reference(root, reference, f"{label}.{field}[{number}]", errors, evidence=field == "evidence")
                result["items"].append(summary)
    if not errors and requirement_id is not None and index is not None and progress is not None:
        state = _check_tracking_state(root, requirement_id, index, progress)
        result["tracking_state_checked"] = state["checked"]
        result["recorded_status"] = state.get("recorded_status")
        for error in state["errors"]:
            errors.append(error)
        if state["requirement_file"] is not None:
            required_files.add(state["requirement_file"])
    result["required_files"] = sorted(required_files)
    return _finish(result)
