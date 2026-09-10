"""按调用方确认的任务与变更事实选择检查；不读取文件、不判断业务完成。"""
from pathlib import PurePosixPath

CHECKS = 'references/checklists/'
VALID_OPERATIONS = {'commit', 'checkpoint', 'push', 'review', 'release', 'health'}
VALID_IMPACTS = {'ui', 'dependencies', 'architecture', 'storage', 'concurrency',
                 'privacy', 'subscription', 'analytics', 'release', 'generation'}


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
        'operation': operation,
        'impacts': sorted(effects),
        'note': '检查选择不是通过结论；调用方须补充路径无法判断的语义影响，纯推送可按相同证据键复用。',
    }
