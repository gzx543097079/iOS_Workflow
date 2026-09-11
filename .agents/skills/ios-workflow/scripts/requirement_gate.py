"""Read-only requirement checks; callers supply task facts, never permissions."""
from pathlib import Path

from project_generation import load_jsonc, ConfigurationError
from resume_context import load_resume_context
from progress_validation import validate_progress_scope


def assess_requirement_gate(project_root, *, task_kind, phase, card,
                            requirement_id=None, low_risk=False, single_turn=False,
                            acceptance_clear=False, continuity_required=False,
                            related_requirement=False):
    """Check start/checkpoint/complete readiness without writing or running tests.

    Only pure maintenance may be exempt. Existing task facts and continuing
    tracking requirements must be carried forward by the caller. A passed gate
    checks recorded facts, not the truth or sufficiency of business acceptance.
    """
    errors = []
    flags = (low_risk, single_turn, acceptance_clear, continuity_required, related_requirement)
    if task_kind not in ("feature", "bug", "maintenance"):
        errors.append("task_kind: 明确区分新增功能、缺陷和纯维护")
    if phase not in ("start", "checkpoint", "complete"):
        errors.append("phase: 必须为 start、checkpoint 或 complete")
    if any(type(value) is not bool for value in flags):
        errors.append("任务判断必须提供布尔值，不能以未知或字符串代替")
    exempt = (not errors and task_kind == "maintenance" and low_risk and single_turn
              and acceptance_clear and not continuity_required and not related_requirement
              and requirement_id is None)
    if not isinstance(card, dict):
        errors.append("缺少精简需求卡")
    else:
        if not isinstance(card.get("goal"), str) or not card["goal"].strip():
            errors.append("需求卡缺少目标")
        for field in ("scope", "acceptance", "exclusions", "assumptions"):
            value = card.get(field)
            if (not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value)
                    or (field in ("scope", "acceptance") and not value)):
                errors.append(f"需求卡 {field} 应为文本列表；范围和验收不能为空")
    if not errors and not exempt:
        if not isinstance(requirement_id, str) or not requirement_id.strip():
            errors.append("本任务必须建档并提供稳定 requirement_id")
        else:
            context = load_resume_context(project_root, requirement_id)
            errors.extend(context["errors"])
            if not errors:
                status = context.get("recorded_status")
                if phase == "start" and status not in ("ready", "in_progress"):
                    errors.append("开始实现前需求须为 ready 或 in_progress；不能继续已归档或阻塞状态")
                if phase == "complete" and status != "done":
                    errors.append("宣告完成前须同步验收账本与终态记录")
                if phase == "complete":
                    try:
                        progress = load_jsonc(Path(project_root) / ".ios-workflow/progress.json")
                        errors.extend(validate_progress_scope(Path(project_root), progress, requirement_ids=[requirement_id]))
                    except (OSError, ConfigurationError, ValueError) as error:
                        errors.append(f"无法检查验收账本: {error}")
    return {"gate_passed": not errors, "tracking_required": not exempt,
            "decision": "exempt_maintenance" if exempt else "tracked",
            "phase": phase, "errors": errors, "metadata_only": True}
