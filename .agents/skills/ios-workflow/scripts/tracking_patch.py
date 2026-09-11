"""Merge selected tracking changes locally, then use the existing transaction API.

This helper updates existing records only. It does not infer task status, run
tests, discard history, or migrate generation inputs or evidence schemas.
"""
import copy
import json
import re

from tracking_state import validate_tracking_state
from resume_context import load_resume_context
from tracking_update import (RECORDS, TrackingUpdateError, _root, _read, _digest,
                             _document, _target_paths, prepare_tracking_update)


ITEM_FIELDS = {"source", "criterion", "status", "implementation", "evidence",
               "archived_evidence", "scope_decision"}
ACTIVE_FIELDS = {"title", "status", "current_step", "next_action", "blockers",
                 "evidence_key", "scope_version", "branch", "observed_head", "updated_at"}
ARCHIVE_FIELDS = {"type", "status", "design_level", "design_status", "branch",
                  "created_at", "updated_at", "workflow_version", "current_step",
                  "next_action", "evidence_key", "scope_version", "observed_head"}


def _snapshot(project_root, requirement_id):
    root = _root(project_root)
    if not isinstance(requirement_id, str) or not requirement_id.strip():
        raise TrackingUpdateError("必须明确已留档的 requirement_id")
    context = load_resume_context(root, requirement_id)
    if context["error_count"] or not context["tracking_state_checked"]:
        raise TrackingUpdateError("先恢复或协调现有摘要：" + "; ".join(context["errors"]))
    state = validate_tracking_state(root, requirement_id)
    if state["errors"] or not state["checked"]:
        raise TrackingUpdateError("先恢复或协调现有记录：" + "; ".join(state["errors"]))
    paths = RECORDS | {state["requirement_file"]}
    contents = {path: _read(root, path) for path in sorted(paths)}
    _target_paths({path: data.decode("utf-8") for path, data in contents.items()})
    return root, state, contents


def read_tracking_snapshot(project_root, requirement_id):
    """Return observed versions, without ledger bodies, evidence, or history."""
    _, state, contents = _snapshot(project_root, requirement_id)
    return {"requirement_id": requirement_id, "recorded_status": state["recorded_status"],
            "expected_hashes": {path: _digest(data) for path, data in contents.items()},
            "metadata_only": True}


def _fields(value, forbidden, label, *, allowed, existing=()):
    if not isinstance(value, dict) or any(not isinstance(k, str) or not k for k in value):
        raise TrackingUpdateError(f"{label}: 必须是字段对象")
    if forbidden.intersection(value):
        raise TrackingUpdateError(f"{label}: 不能修改稳定标识、归属或执行序号")
    if set(value) - set(allowed) - set(existing):
        raise TrackingUpdateError(f"{label}: 未知字段；新增扩展字段须使用完整候选接口")
    return copy.deepcopy(value)


def _validate_active(active):
    """Match the mutable recovery fields accepted by load_resume_context.

    Long descriptive strings are valid and displayed with disclosed truncation;
    a step identifier cannot be truncated. Record links and statuses are checked
    by the existing transaction validator after local merging.
    """
    for key in ("title", "evidence_key", "branch", "observed_head", "updated_at", "next_action"):
        if not isinstance(active.get(key), str):
            raise TrackingUpdateError(f"active_requirement.{key}: 必须是字符串")
    step = active.get("current_step")
    if not isinstance(step, str) or len(step) > 256:
        raise TrackingUpdateError("active_requirement.current_step: 必须是最长 256 字符的字符串")
    version = active.get("scope_version")
    if type(version) is not int or version < 1:
        raise TrackingUpdateError("active_requirement.scope_version: 必须是正整数")
    blockers = active.get("blockers")
    if not isinstance(blockers, list) or any(not isinstance(v, str) or not v.strip() for v in blockers):
        raise TrackingUpdateError("active_requirement.blockers: 必须是非空字符串组成的数组")


def _edit_archive(text, change):
    if not isinstance(change, dict) or set(change) - {"metadata", "append"}:
        raise TrackingUpdateError("archive: 仅支持 metadata 和 append")
    appendix = change.get("append", "")
    if not isinstance(appendix, str):
        raise TrackingUpdateError("archive.append: 必须是文本")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise TrackingUpdateError("档案缺少 frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise TrackingUpdateError("档案 frontmatter 不完整")
    existing = {line.partition(":")[0] for line in lines[1:end]
                if re.match(r"[A-Za-z_][A-Za-z0-9_]*:", line)}
    metadata = _fields(change.get("metadata", {}), {"id", "project", "sequence"},
                       "archive.metadata", allowed=ARCHIVE_FIELDS, existing=existing)
    for key, value in metadata.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or not (value is None or type(value) in (str, int, bool)):
            raise TrackingUpdateError("archive.metadata: 仅支持平面标量字段")
    updated = [lines[0]]
    for line in lines[1:end]:
        key = line.partition(":")[0]
        if key in metadata:
            value = metadata.pop(key)
            updated.append(f"{key}: {json.dumps(value, ensure_ascii=False)}\n")
        else:
            updated.append(line)
    updated.extend(f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in metadata.items())
    updated.extend(lines[end:])
    result = "".join(updated)
    if appendix:
        result += ("" if result.endswith("\n") else "\n") + appendix
        if not result.endswith("\n"):
            result += "\n"
    return result


def prepare_tracking_patch(project_root, requirement_id, updates, expected_hashes):
    """Prepare explicit field changes against versions observed before editing.

    Omitted fields retain their values; supplied arrays replace only that field.
    Standard fields and already-recorded extension keys can be updated. Adding
    extension keys, requirements/acceptance IDs or rewriting archive sections
    uses the complete-candidate API instead. Applying/recovering uses tracking_update.
    """
    if not isinstance(updates, dict) or not updates or set(updates) - {
            "items", "active_requirement", "history_entry", "archive"}:
        raise TrackingUpdateError("updates: 提供 items/active_requirement/history_entry/archive 中的变更")
    root, state, contents = _snapshot(project_root, requirement_id)
    hashes = {path: _digest(data) for path, data in contents.items()}
    if not isinstance(expected_hashes, dict) or expected_hashes != hashes:
        raise TrackingUpdateError("旧哈希或文件版本已变化；重新检查外部修改，不能自动更新基线")
    candidates = {path: data.decode("utf-8") for path, data in contents.items()}
    changed = set()
    if "items" in updates:
        values = updates["items"]
        if not isinstance(values, list) or not values:
            raise TrackingUpdateError("items: 必须是非空变更数组")
        path = ".ios-workflow/progress.json"
        document = _document(contents[path])
        selected = {item["id"]: item for item in document["items"] if item["requirement_id"] == requirement_id}
        seen = set()
        for update in values:
            if not isinstance(update, dict) or set(update) != {"id", "set"} or not isinstance(update["id"], str):
                raise TrackingUpdateError("items: 每项必须有 id 和 set")
            identifier = update["id"]
            if identifier not in selected or identifier in seen:
                raise TrackingUpdateError("items: ID 不属于本需求、尚未建档或重复")
            seen.add(identifier)
            selected[identifier].update(_fields(update["set"], {"id", "requirement_id"}, "items.set",
                                               allowed=ITEM_FIELDS, existing=selected[identifier]))
        candidates[path] = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        changed.add(path)
    if "active_requirement" in updates:
        path = ".ios-workflow/index.jsonc"
        document = _document(contents[path])
        active = document.get("active_requirement")
        if not isinstance(active, dict) or active.get("id") != requirement_id:
            raise TrackingUpdateError("active_requirement: 只能更新当前选定的活动需求")
        values = updates["active_requirement"]
        if values is None:
            document["active_requirement"] = None
            document["last_requirement_id"] = requirement_id
        else:
            active.update(_fields(values, {"id", "project", "file", "sequence"}, "active_requirement",
                                  allowed=ACTIVE_FIELDS, existing=active))
            _validate_active(active)
        candidates[path] = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        changed.add(path)
    if "history_entry" in updates:
        path = ".ios-workflow/history.jsonc"
        document = _document(contents[path])
        rows = [row for row in document["execution_order"] if row["id"] == requirement_id]
        if len(rows) != 1:
            raise TrackingUpdateError("history_entry: 选定需求尚未登记执行行")
        rows[0].update(_fields(updates["history_entry"], {"id", "project", "file", "sequence"},
                              "history_entry", allowed={"status"}, existing=rows[0]))
        candidates[path] = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        changed.add(path)
    if "archive" in updates:
        path = state["requirement_file"]
        candidates[path] = _edit_archive(candidates[path], updates["archive"])
        changed.add(path)
    identifier = prepare_tracking_update(root, requirement_id, candidates, expected_hashes)
    return {"transaction_id": identifier, "state": "prepared", "requirement_id": requirement_id,
            "changed_files": sorted(path for path in changed if candidates[path].encode("utf-8") != contents[path]),
            "metadata_only": True}
