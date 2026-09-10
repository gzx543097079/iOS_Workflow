"""Record and compare evidence from actual project files without changing them.

These helpers never run tests, verify report contents or promote progress states.
Callers supply results from actual execution and the complete affected input set.
``matched`` only means the recorded files, inputs and environment still match.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from .progress_validation import EVIDENCE_RESULTS, SKILL_ROOT, _file, _valid_recorded_at, _within
except ImportError:
    from progress_validation import EVIDENCE_RESULTS, SKILL_ROOT, _file, _valid_recorded_at, _within


ENVIRONMENT_FIELDS = ("xcode", "sdk", "scheme", "configuration", "destination", "test_selection")
UNKNOWN_VALUES = frozenset({"unknown", "incomplete", "not_run", "not run", "n/a", "tbd", "未知", "待补充"})


def _project_root(project_root: Any) -> Path:
    try:
        root = Path(project_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ValueError("project_root: 项目目录不存在或无法读取") from error
    if not root.is_dir() or _within(root, SKILL_ROOT):
        raise ValueError("project_root: 必须是业务项目目录，不能是 Skill 或其子目录")
    return root


def resolve_project_file(project_root: Path, path: str, *, evidence: bool = False) -> Path:
    """Resolve an existing portable project file, rejecting unsafe references."""
    root = _project_root(project_root)
    errors: list[str] = []
    resolved = _file(root, path, "path", errors, evidence=evidence)
    if errors or resolved is None:
        raise ValueError("; ".join(errors))
    return resolved


def file_sha256(path: Path) -> str:
    """Hash actual file bytes in bounded chunks; never write a report."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError("文件无法读取，不能计算 SHA-256") from error
    return digest.hexdigest()


def _known_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in UNKNOWN_VALUES


def _environment_values(environment: Any) -> dict:
    if not isinstance(environment, dict):
        raise ValueError("environment: 必须是包含实际受测环境的对象")
    errors = []
    values = {}
    for key in ENVIRONMENT_FIELDS:
        value = environment.get(key)
        if key == "test_selection" and isinstance(value, list):
            if value and all(_known_string(item) for item in value):
                values[key] = sorted(set(item.strip() for item in value))
                continue
        if _known_string(value):
            values[key] = value.strip()
        else:
            errors.append(f"environment.{key}: 必须记录非空实际值，不能使用 unknown/incomplete 等占位")
    # Preserve extra environment dimensions so runtime/toolchain details supplied
    # by the project also participate in reuse decisions.
    for key, value in environment.items():
        if key in ENVIRONMENT_FIELDS:
            continue
        if _known_string(key) and _known_string(value):
            values[key] = value.strip()
        else:
            errors.append("environment: 额外环境字段必须是非空字符串键和值")
    if errors:
        raise ValueError("; ".join(errors))
    return values


def _fingerprint(values: dict) -> str:
    encoded = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _environment_summary(values: dict) -> str:
    return "; ".join(f"{key}={json.dumps(value, ensure_ascii=False)}" for key, value in sorted(values.items()))


def _input_paths(root: Path, input_paths: Any) -> dict[str, Path]:
    if not isinstance(input_paths, (list, tuple)) or not input_paths:
        raise ValueError("input_paths: 必须显式提供非空受测输入路径数组")
    files = {}
    for path in input_paths:
        resolved = resolve_project_file(root, path)
        files[PurePosixPath(path).as_posix()] = resolved
    return files


def capture_evidence(project_root: Path, evidence_path: str, input_paths: list[str],
                     environment: dict, result: str, recorded_at: str | None = None) -> dict:
    """Return evidence metadata from existing files; raise ValueError if incomplete.

    ``result`` must come from the actual execution record. This helper cannot
    determine whether a caller's claim agrees with the report or acceptance item.
    Required environment fields are strings; test_selection also accepts a list
    of test identifiers. Include platform/runtime details in destination or extra
    string fields. Save the returned object in the business project's ledger.
    """
    root = _project_root(project_root)
    if not isinstance(result, str) or result not in EVIDENCE_RESULTS:
        raise ValueError("result: 必须是实际记录的 passed/failed/blocked/skipped")
    timestamp = recorded_at if recorded_at is not None else datetime.now(timezone.utc).isoformat()
    if not _valid_recorded_at(timestamp):
        raise ValueError("recorded_at: 必须是含时区的有效 ISO 8601 时间")
    values = _environment_values(environment)
    evidence = resolve_project_file(root, evidence_path, evidence=True)
    inputs = _input_paths(root, input_paths)
    return {
        "path": PurePosixPath(evidence_path).as_posix(),
        "sha256": file_sha256(evidence),
        "inputs": [{"path": path, "sha256": file_sha256(inputs[path])} for path in sorted(inputs)],
        "environment": _environment_summary(values),
        "environment_fingerprint": {"schema_version": 1, "values": values, "sha256": _fingerprint(values)},
        "result": result,
        "recorded_at": timestamp,
    }


def compare_evidence(project_root: Path, record: dict, current_environment: dict,
                     current_input_paths: list[str]) -> dict:
    """Return matched/stale/unknown and reasons, without updating the record.

    Missing or invalid data and inaccessible files produce unknown. A complete
    comparison reports stale for unsuccessful results or changed files, input
    sets or environments. Unknown takes precedence if comparison is incomplete.
    """
    unknown: list[str] = []
    stale: list[str] = []
    try:
        root = _project_root(project_root)
    except ValueError as error:
        return {"status": "unknown", "reasons": [str(error)]}
    if not isinstance(record, dict):
        return {"status": "unknown", "reasons": ["record: 必须是证据对象"]}

    result = record.get("result")
    if not isinstance(result, str) or result not in EVIDENCE_RESULTS:
        unknown.append("result: 缺失或未知的实际执行结果")
    elif result != "passed":
        stale.append(f"result: 当前证据结果为 {result}，不可复用为成功证据")
    if not _valid_recorded_at(record.get("recorded_at")):
        unknown.append("recorded_at: 缺失或不是含时区的有效 ISO 8601 时间")
    if not _known_string(record.get("environment")):
        unknown.append("environment: 缺失实际环境说明")

    current_values = None
    try:
        current_values = _environment_values(current_environment)
    except ValueError as error:
        unknown.append(str(error))
    fingerprint = record.get("environment_fingerprint")
    if (not isinstance(fingerprint, dict) or type(fingerprint.get("schema_version")) is not int
            or fingerprint.get("schema_version") != 1):
        unknown.append("environment_fingerprint: 缺失或不支持的环境指纹")
    else:
        try:
            values = _environment_values(fingerprint.get("values"))
            stored_hash = fingerprint.get("sha256")
            if not isinstance(stored_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", stored_hash):
                unknown.append("environment_fingerprint.sha256: 缺失或无效")
            else:
                if _fingerprint(values) != stored_hash.lower():
                    stale.append("environment_fingerprint: 保存的环境内容与指纹不一致")
                if current_values is not None and _fingerprint(current_values) != stored_hash.lower():
                    stale.append("environment_fingerprint: 当前环境或测试选择已变化")
        except ValueError as error:
            unknown.append(str(error))

    def check_file(entry: Any, label: str, *, evidence: bool = False) -> str | None:
        if not isinstance(entry, dict):
            unknown.append(f"{label}: 必须是文件记录对象")
            return None
        expected = entry.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            unknown.append(f"{label}.sha256: 缺失或无效")
        try:
            path = resolve_project_file(root, entry.get("path"), evidence=evidence)
            digest = file_sha256(path)
            if isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected) and digest != expected.lower():
                stale.append(f"{label}: 文件已变化 {entry['path']}")
            return PurePosixPath(entry["path"]).as_posix()
        except ValueError as error:
            unknown.append(f"{label}: {error}")
            return None

    check_file(record, "evidence", evidence=True)
    recorded_paths = set()
    recorded_inputs = record.get("inputs")
    if not isinstance(recorded_inputs, list) or not recorded_inputs:
        unknown.append("inputs: 缺失非空受测输入数组")
    else:
        for index, entry in enumerate(recorded_inputs):
            path = check_file(entry, f"inputs[{index}]")
            if path is not None:
                if path in recorded_paths:
                    unknown.append(f"inputs[{index}]: 重复输入路径 {path}")
                recorded_paths.add(path)
    try:
        current_paths = set(_input_paths(root, current_input_paths))
        if recorded_paths != current_paths:
            added = sorted(current_paths - recorded_paths)
            removed = sorted(recorded_paths - current_paths)
            stale.append(f"inputs: 当前输入集合已变化；新增={added}，移除={removed}")
    except ValueError as error:
        unknown.append(str(error))
    return {"status": "unknown" if unknown else "stale" if stale else "matched", "reasons": unknown + stale}
