"""按调用方确认的任务与变更事实选择检查；不读取文件、不判断业务完成。"""
from pathlib import PurePosixPath

CHECKS = 'references/checklists/'
VALID_OPERATIONS = {'commit', 'checkpoint', 'push', 'review', 'release', 'health'}
VALID_IMPACTS = {'ui', 'dependencies', 'architecture', 'storage', 'concurrency',
                 'privacy', 'subscription', 'analytics', 'release', 'generation'}
INTEGRITY_CHECKS = frozenset({'scope', 'privacy', 'user_files', 'records'})
VALIDATION_RESULTS = frozenset({'passed', 'failed', 'unknown', 'blocked', 'skipped', 'not_required'})


def select_checks(changed_paths, *, operation='commit', impacts=(), requirement_ids=()):
    """返回需加载的清单与追溯范围。impacts 由 diff 语义判断，路径仅补充线索。"""
    if operation not in VALID_OPERATIONS:
        raise ValueError('operation 必须为 commit/checkpoint/push/review/release/health')
    if not isinstance(changed_paths, (list, tuple)) or not all(isinstance(p, str) and p for p in changed_paths):
        raise ValueError('changed_paths 必须为项目相对路径数组')
    paths = []
    for path in changed_paths:
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or '..' in normalized.parts or '\\' in path or ':' in path:
            raise ValueError('changed_paths 必须位于项目内')
        paths.append(normalized)
    if not isinstance(impacts, (list, tuple, set, frozenset)) or not all(isinstance(i, str) and i in VALID_IMPACTS for i in impacts):
        raise ValueError('impacts 包含不支持的语义影响')
    if not isinstance(requirement_ids, (list, tuple)) or not all(isinstance(i, str) and i.strip() for i in requirement_ids):
        raise ValueError('requirement_ids 必须为明确的需求 ID 数组')
    effects = set(impacts)
    suffixes = {p.suffix.lower() for p in paths}
    names = {p.name for p in paths}
    if names & {'Podfile', 'Podfile.lock', 'Package.swift', 'Package.resolved', 'Cartfile', 'Cartfile.resolved'}:
        effects.add('dependencies')
    if names & {'project_generation.py', 'project.example.jsonc'}:
        effects.add('generation')
    tests_affected = bool(suffixes & {'.swift', '.m', '.mm', '.h', '.py', '.plist', '.entitlements', '.xcconfig', '.pbxproj', '.yml', '.yaml', '.xcprivacy'})
    if suffixes & {'.entitlements', '.xcprivacy'}:
        effects.add('privacy')
    if '.entitlements' in suffixes:
        effects.add('release')
    if operation == 'release':
        effects.add('release')
    checks = ['core.md']
    if effects & {'architecture', 'storage', 'concurrency', 'dependencies', 'privacy'}:
        checks.append('technical-design.md')
    if 'generation' in effects:
        checks.append('project-generation.md')
    if tests_affected or effects:
        checks.append('testing.md')
    for effect, check in [('subscription', 'subscription.md'), ('analytics', 'analytics.md'), ('release', 'release-distribution.md')]:
        if effect in effects:
            checks.append(check)
    ids = list(dict.fromkeys(requirement_ids))
    if ids or operation == 'health':
        checks.append('requirement-traceability.md')
    return {
        'checks': [CHECKS + check for check in checks],
        'requirements': ids,
        'progress_scope': 'all' if operation == 'health' else ('selected' if ids else 'none'),
        'completion_required': operation == 'release',
        'validation_required': 'testing.md' in checks,
        'operation': operation,
        'impacts': sorted(effects),
        'note': '检查选择不是通过结论；调用方须补充路径无法判断的语义影响，纯推送可按相同证据键复用。',
    }


def assess_gate(changed_paths, *, integrity, operation='commit', impacts=(), requirement_ids=(),
                validation_result='unknown', completion_result='unknown'):
    """Evaluate declared checks for this operation without executing or promoting anything.

    The caller records observed ``scope``, ``privacy``, ``user_files`` and
    ``records`` checks as passed/failed/unknown. This function does not inspect
    files or infer their truth. A checkpoint may preserve failed or unknown
    validation, including its separately authorized synchronization; ordinary
    delivery still requires relevant validation. Passing this gate grants no
    Git or release authorization and never changes acceptance status.
    """
    selection = select_checks(changed_paths, operation=operation, impacts=impacts,
                              requirement_ids=requirement_ids)
    if not isinstance(integrity, dict) or set(integrity) != INTEGRITY_CHECKS:
        raise ValueError('integrity 必须显式提供 scope/privacy/user_files/records 检查')
    if not all(isinstance(value, str) and value in {'passed', 'failed', 'unknown'}
               for value in integrity.values()):
        raise ValueError('integrity 结果必须为 passed/failed/unknown')
    if not isinstance(validation_result, str) or validation_result not in VALIDATION_RESULTS:
        raise ValueError('validation_result 必须是明确的验证状态')
    if not isinstance(completion_result, str) or completion_result not in {'passed', 'failed', 'unknown'}:
        raise ValueError('completion_result 必须为 passed/failed/unknown')

    blockers = [f'integrity.{name}:{integrity[name]}' for name in sorted(INTEGRITY_CHECKS)
                if integrity[name] != 'passed']
    validation_required = selection['validation_required']
    if operation != 'checkpoint':
        if validation_required and validation_result != 'passed':
            blockers.append(f'validation:{validation_result}')
        elif validation_result in {'failed', 'blocked'}:
            blockers.append(f'validation:{validation_result}')
    if selection['completion_required'] and completion_result != 'passed':
        blockers.append(f'completion:{completion_result}')
    if completion_result == 'passed' and validation_required and validation_result != 'passed':
        blockers.append('completion:successful_validation_missing')

    return {
        **selection,
        'gate_passed': not blockers,
        'integrity': dict(integrity),
        'validation_result': validation_result,
        'validation_passed': validation_result == 'passed',
        'completion_result': completion_result,
        'blocking_reasons': blockers,
        'note': '仅按调用方已核实的检查结果判断本次门禁；不执行操作、不授予权限、不提升验收状态。',
    }
