"""Stage, validate and explicitly recover multi-file project tracking updates.

Each target replacement is atomic; the four-file update is not. POSIX flock
serializes cooperating callers and is released by the OS after a crash. Editors
do not honor this lock: stop concurrent editing while applying an update.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath

from project_generation import ConfigurationError, load_jsonc, strip_jsonc
from progress_validation import SKILL_ROOT, _within, validate_progress_scope
from tracking_state import validate_tracking_state


TRANSACTIONS = ".ios-workflow/transactions"
RECORDS = {".ios-workflow/index.jsonc", ".ios-workflow/progress.json", ".ios-workflow/history.jsonc"}


class TrackingUpdateError(ValueError):
    """The candidate or observed filesystem state does not permit this update."""


def _root(value) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise TrackingUpdateError("项目目录不存在或无法读取") from error
    if not root.is_dir() or _within(root, SKILL_ROOT):
        raise TrackingUpdateError("必须使用 Skill 之外的业务项目目录")
    return root


def _path(value) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise TrackingUpdateError("必须提供项目相对路径")
    path = PurePosixPath(value)
    if path.is_absolute() or PureWindowsPath(value).drive or ".." in path.parts or path.as_posix() != value:
        raise TrackingUpdateError("路径必须规范化且位于项目内")
    if value in ("workflow.json", ".ios-workflow/project.json") or value.startswith(".ios-workflow/generation/"):
        raise TrackingUpdateError("进度更新不读取或核对历史生成配置")
    if not path.name or value == ".":
        raise TrackingUpdateError("路径必须指向文件")
    return value


@contextmanager
def _parent(root: Path, relative: str, *, create=False):
    parts = PurePosixPath(_path(relative)).parts
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def _read(root: Path, relative: str, *, missing=False) -> bytes | None:
    if _within(root / _path(relative), SKILL_ROOT):
        raise TrackingUpdateError("不能把 Skill 文件作为业务项目的执行输入")
    try:
        with _parent(root, relative) as (parent, name):
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise TrackingUpdateError(f"{relative}: 必须是普通文件")
                return stream.read()
    except FileNotFoundError:
        if missing:
            return None
        raise TrackingUpdateError(f"{relative}: 文件缺失")
    except OSError as error:
        raise TrackingUpdateError(f"{relative}: 无法安全读取文件，禁止符号链接") from error


def _digest(content: bytes | None) -> str | None:
    return None if content is None else hashlib.sha256(content).hexdigest()


def _write(root: Path, relative: str, content: bytes, *, expected=None, replace=False):
    """Write within anchored directories; never follow a target symlink."""
    with _parent(root, relative, create=True) as (parent, name):
        temporary = f".{name}.{uuid.uuid4().hex}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if replace:
                if _digest(_read(root, relative, missing=True)) != expected:
                    raise TrackingUpdateError(f"{relative}: 写入前检测到外部修改，停止覆盖")
                if expected is not None:
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                else:
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            else:
                os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.fsync(parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


@contextmanager
def _lock(root: Path):
    with _parent(root, f"{TRANSACTIONS}/.lock", create=True) as (parent, name):
        descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise TrackingUpdateError("事务锁必须是普通文件")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise TrackingUpdateError("另一个进度更新正在执行，请稍后重试") from error
            yield
        finally:
            os.close(descriptor)


def _target_paths(candidates) -> list[str]:
    if not isinstance(candidates, dict) or not all(isinstance(value, str) for value in candidates.values()):
        raise TrackingUpdateError("candidates 必须是项目相对路径到完整 UTF-8 文本的对象")
    paths = {_path(path) for path in candidates}
    archives = paths - RECORDS
    if not RECORDS.issubset(paths) or len(archives) != 1:
        raise TrackingUpdateError("必须提供 index/progress/history 和一个完整需求档案，共四个候选文件")
    archive = next(iter(archives))
    if not archive.startswith(".ios-workflow/requirements/") or not archive.endswith(".md"):
        raise TrackingUpdateError("指定需求档案必须位于 .ios-workflow/requirements/ 且为 Markdown")
    return sorted(paths)


def _document(content) -> dict:
    try:
        value = json.loads(strip_jsonc(content.decode("utf-8") if isinstance(content, bytes) else content))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise TrackingUpdateError("记录不是可读取的 JSON 对象，先明确修复，不自动丢弃旧内容") from error
    if not isinstance(value, dict):
        raise TrackingUpdateError("记录必须是 JSON 对象")
    return value


def _preserve_existing(old: dict, candidates: dict, requirement_id: str):
    """A selected requirement cannot erase or rewrite another requirement."""
    for path, key in ((".ios-workflow/progress.json", "items"), (".ios-workflow/history.jsonc", "execution_order")):
        if old[path] is None:
            continue
        previous, following = _document(old[path]), _document(candidates[path])
        before, after = previous.get(key), following.get(key)
        if not isinstance(before, list) or not isinstance(after, list):
            raise TrackingUpdateError(f"{path}: 缺少可核对的记录数组")
        maps = []
        for values in (before, after):
            mapping = {}
            for entry in values:
                if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"].strip() or entry["id"] in mapping:
                    raise TrackingUpdateError(f"{path}: 记录 ID 无效或重复，不能自动合并")
                mapping[entry["id"]] = entry
            maps.append(mapping)
        first, second = maps
        if not set(first).issubset(second):
            raise TrackingUpdateError(f"{path}: 不得删除已有验收 ID 或执行记录；范围变化须保留延期/取消项")
        for identifier, entry in first.items():
            owner = entry.get("requirement_id") if key == "items" else identifier
            if not isinstance(owner, str) or not owner.strip():
                raise TrackingUpdateError(f"{path}: 旧记录缺少需求关联，无法安全更新")
            if owner != requirement_id and entry != second[identifier]:
                raise TrackingUpdateError(f"{path}: 不得修改其他需求的记录")
            if key == "items" and second[identifier].get("requirement_id") != owner:
                raise TrackingUpdateError("progress: 不得改变已有验收 ID 的所属需求")
            if key == "execution_order" and entry.get("sequence") != second[identifier].get("sequence"):
                raise TrackingUpdateError("history: 不得改写已有执行序号")
        for identifier in set(second) - set(first):
            owner = second[identifier].get("requirement_id") if key == "items" else identifier
            if owner != requirement_id:
                raise TrackingUpdateError(f"{path}: 本事务不能新增其他需求的记录")
        if key == "execution_order":
            before_ids = list(first)
            after_ids = [entry["id"] for entry in after if entry["id"] in first]
            if before_ids != after_ids:
                raise TrackingUpdateError("history: 不得重排已有执行记录")
            old_next, new_next = previous.get("next_sequence"), following.get("next_sequence")
            if type(old_next) is not int or type(new_next) is not int or new_next < old_next:
                raise TrackingUpdateError("history: 不得降低 next_sequence 或猜测旧序号")
            if any(type(second[key].get("sequence")) is not int or second[key]["sequence"] < old_next
                   for key in set(second) - set(first)):
                raise TrackingUpdateError("history: 新执行记录不能复用旧 next_sequence 之前的序号")
    index_path = ".ios-workflow/index.jsonc"
    if old[index_path] is not None:
        active = _document(old[index_path]).get("active_requirement")
        if isinstance(active, dict) and active.get("id") != requirement_id:
            if _document(candidates[index_path]).get("active_requirement") != active:
                raise TrackingUpdateError("index: 不能覆盖其他需求的活动摘要")


def _references(progress: dict, requirement_id: str) -> set[str]:
    references = set()
    items = progress.get("items")
    if not isinstance(items, list):
        raise TrackingUpdateError("progress.items 必须是数组")
    for item in items:
        if not isinstance(item, dict) or item.get("requirement_id") != requirement_id:
            continue
        source = item.get("source")
        if isinstance(source, dict):
            references.add(_path(source.get("path")))
        for path in item.get("implementation", []) if isinstance(item.get("implementation"), list) else []:
            references.add(_path(path))
        evidence = item.get("evidence")
        for entry in evidence if isinstance(evidence, list) else []:
            if not isinstance(entry, dict):
                continue
            references.add(_path(entry.get("path")))
            inputs = entry.get("inputs")
            for value in inputs if isinstance(inputs, list) else []:
                if isinstance(value, dict):
                    references.add(_path(value.get("path")))
        decision = item.get("scope_decision")
        if isinstance(decision, dict) and isinstance(decision.get("source"), dict):
            references.add(_path(decision["source"].get("path")))
    return references


def _validate_snapshot(root: Path, base: str, candidates: dict, requirement_id: str) -> dict:
    for path, content in candidates.items():
        _write(root, f"{base}/candidate/{path}", content.encode("utf-8"))
    snapshot = root / base / "candidate"
    try:
        progress = load_jsonc(snapshot / ".ios-workflow/progress.json")
        inputs = {}
        for path in sorted(_references(progress, requirement_id) - set(candidates)):
            content = _read(root, path)
            inputs[path] = _digest(content)
            _write(root, f"{base}/candidate/{path}", content)
        state = validate_tracking_state(snapshot, requirement_id)
        errors = state["errors"]
        archive = next(path for path in candidates if path not in RECORDS)
        if state["requirement_file"] != archive:
            errors.append("选定需求实际校验的档案必须就是本事务提供的候选档案")
        errors += validate_progress_scope(snapshot, progress, requirement_ids=[requirement_id])
        if errors:
            raise TrackingUpdateError("候选记录校验失败：" + "; ".join(errors))
        # Inputs exist only for validation. Retain their hashes, not business
        # source/report copies, in the portable recovery record.
        for path in inputs:
            with _parent(root, f"{base}/candidate/{path}") as (parent, name):
                os.unlink(name, dir_fd=parent)
        return inputs
    except (ConfigurationError, UnicodeError, RecursionError) as error:
        raise TrackingUpdateError("候选记录不是可读取的受支持格式") from error


def prepare_tracking_update(project_root: Path, requirement_id: str, candidates: dict,
                            expected_hashes: dict) -> str:
    """Validate a complete candidate, retain recovery data and return its ID.

    expected_hashes covers exactly the four targets: actual SHA-256 for existing
    files and None only for absent files. No target is written during preparation.
    An invalid candidate's staging directory is removed; the lock file may remain.
    """
    root = _root(project_root)
    paths = _target_paths(candidates)
    if not isinstance(requirement_id, str) or not requirement_id.strip() or len(requirement_id) > 256:
        raise TrackingUpdateError("requirement_id 必须是非空稳定 ID，最长 256 字符")
    if (not isinstance(expected_hashes, dict) or set(expected_hashes) != set(paths)
            or any(value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value))
                   for value in expected_hashes.values())):
        raise TrackingUpdateError("expected_hashes 必须覆盖四个目标的实际小写 SHA-256，缺失文件填 null")
    with _lock(root):
        for path in (root / TRANSACTIONS).iterdir():
            if re.fullmatch(r"[0-9a-f]{32}", path.name):
                journal = f"{TRANSACTIONS}/{path.name}/journal.json"
                if (_read(root, journal, missing=True) is not None
                        and _read(root, f"{TRANSACTIONS}/{path.name}/complete", missing=True) is None
                        and _read(root, f"{TRANSACTIONS}/{path.name}/abandoned", missing=True) is None):
                    raise TrackingUpdateError(f"存在未完成事务 {path.name}，先显式恢复，不能排队覆盖同一旧状态")
        old = {path: _read(root, path, missing=True) for path in paths}
        for path in paths:
            if _digest(old[path]) != expected_hashes[path]:
                raise TrackingUpdateError(f"{path}: 旧哈希或文件版本已变化")
        _preserve_existing(old, candidates, requirement_id)
        transaction_id = uuid.uuid4().hex
        base = f"{TRANSACTIONS}/{transaction_id}"
        try:
            inputs = _validate_snapshot(root, base, candidates, requirement_id)
            journal = {"schema_version": 1, "requirement_id": requirement_id, "inputs": inputs,
                       "files": [{"path": path, "old_sha256": expected_hashes[path],
                                  "new_sha256": _digest(candidates[path].encode("utf-8"))} for path in paths]}
            _write(root, f"{base}/journal.json", json.dumps(journal, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        except Exception:
            # Before publishing a journal no target can have been changed.
            staging = root / base
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise
    return transaction_id


def apply_tracking_update(project_root: Path, transaction_id: str) -> dict:
    """Apply or finish an explicitly selected transaction; conflicts stop writes.

    A write interruption leaves its journal and candidate files for recovery.
    All targets are preflighted before any replacement; each must still contain
    its recorded old or new bytes. Relevant validation inputs must also match.
    """
    root = _root(project_root)
    if not isinstance(transaction_id, str) or not re.fullmatch(r"[0-9a-f]{32}", transaction_id):
        raise TrackingUpdateError("transaction_id 无效")
    base = f"{TRANSACTIONS}/{transaction_id}"
    with _lock(root):
        if _read(root, f"{base}/abandoned", missing=True) is not None:
            raise TrackingUpdateError("事务已明确放弃，不能重新应用；请核对当前文件后准备新事务")
        try:
            journal = json.loads(_read(root, f"{base}/journal.json"))
            entries = journal["files"]
            if type(journal.get("schema_version")) is not int or journal["schema_version"] != 1 or not isinstance(entries, list):
                raise ValueError()
            candidates = {entry["path"]: _read(root, f"{base}/candidate/{_path(entry['path'])}") for entry in entries}
            _target_paths({path: content.decode("utf-8") for path, content in candidates.items()})
            if len(entries) != 4 or not isinstance(journal.get("inputs"), dict):
                raise ValueError()
            if any(not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                   for digest in journal["inputs"].values()):
                raise ValueError()
            for entry in entries:
                old, new = entry["old_sha256"], entry["new_sha256"]
                if (old is not None and (not isinstance(old, str) or not re.fullmatch(r"[0-9a-f]{64}", old))
                        or not isinstance(new, str) or not re.fullmatch(r"[0-9a-f]{64}", new)
                        or _digest(candidates[entry["path"]]) != new):
                    raise ValueError()
        except (KeyError, TypeError, ValueError, RecursionError) as error:
            raise TrackingUpdateError("事务记录损坏或候选文件已变化，停止恢复") from error
        for path, digest in journal["inputs"].items():
            if _digest(_read(root, _path(path), missing=True)) != digest:
                raise TrackingUpdateError(f"{path}: 验证输入已变化，不能应用旧候选")
        completed = _read(root, f"{base}/complete", missing=True) is not None
        for entry in entries:
            observed = _digest(_read(root, entry["path"], missing=True))
            allowed = (entry["new_sha256"],) if completed else (entry["old_sha256"], entry["new_sha256"])
            if observed not in allowed:
                raise TrackingUpdateError(f"{entry['path']}: 存在外部修改，停止恢复且不覆盖")
        for entry in entries:
            if _digest(_read(root, entry["path"], missing=True)) == entry["new_sha256"]:
                continue
            _write(root, entry["path"], candidates[entry["path"]], expected=entry["old_sha256"], replace=True)
        for entry in entries:
            if _digest(_read(root, entry["path"], missing=True)) != entry["new_sha256"]:
                raise TrackingUpdateError(f"{entry['path']}: 更新期间有外部修改，不能报告完成")
        for path, digest in journal["inputs"].items():
            if _digest(_read(root, _path(path), missing=True)) != digest:
                raise TrackingUpdateError(f"{path}: 更新期间验证输入变化，保留待恢复记录，不能报告完成")
        if _read(root, f"{base}/complete", missing=True) is None:
            _write(root, f"{base}/complete", b"complete\n")
        return {"transaction_id": transaction_id, "state": "complete", "metadata_only": True}


def recover_tracking_update(project_root: Path, transaction_id: str) -> dict:
    """Explicitly finish an interrupted update under the same conflict checks."""
    return apply_tracking_update(project_root, transaction_id)


def abandon_tracking_update(project_root: Path, transaction_id: str) -> dict:
    """Mark a transaction abandoned without reverting or overwriting any target.

    Retain all recovery data. Callers must inspect and reconcile the current four
    records, including any partial writes or external edits, before preparing a
    new candidate against newly observed hashes. This never repairs state itself.
    """
    root = _root(project_root)
    if not isinstance(transaction_id, str) or not re.fullmatch(r"[0-9a-f]{32}", transaction_id):
        raise TrackingUpdateError("transaction_id 无效")
    base = f"{TRANSACTIONS}/{transaction_id}"
    with _lock(root):
        _read(root, f"{base}/journal.json")
        if _read(root, f"{base}/complete", missing=True) is not None:
            raise TrackingUpdateError("已完成事务无需放弃")
        if _read(root, f"{base}/abandoned", missing=True) is None:
            _write(root, f"{base}/abandoned", b"abandoned; targets retained without rollback\n")
    return {"transaction_id": transaction_id, "state": "abandoned", "requires_reconciliation": True}
