"""Compile generated iOS fixtures; no signing, App execution or business acceptance."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
from project_generation import generate_project, generate_xcodeproj, load_project_instance, save_project_instance

CASES = {
    'swift-uikit-5': ('swift', 'uikit', '5'),
    'swift-uikit-6': ('swift', 'uikit', '6'),
    'swiftui-5': ('swift', 'swiftui', '5'),
    'swiftui-6': ('swift', 'swiftui', '6'),
    'objc-uikit': ('objc', 'uikit', '5'),
}


def check_case(case: str, output: Path) -> dict:
    """Raise on missing tools or failed compilation; write real results to the fixture."""
    if case not in CASES:
        raise ValueError('Unknown generated-project case')
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Fixture output must be empty; existing results are never reused')
    for tool in ('xcodegen', 'xcodebuild'):
        if not shutil.which(tool):
            raise RuntimeError(f'Required tool unavailable: {tool}')
    language, ui, mode = CASES[case]
    instance = load_project_instance(ROOT / 'distribution/project.example.jsonc')
    instance['project_name'] = 'WorkflowBuildFixture'
    instance['config'].update(language=language, ui=ui, swift_version=mode,
                              dependency_manager='none', include_unit_tests=True, include_ui_tests=True,
                              supports_manual_dark_mode_switch=True, generate_xcodeproj=True)
    for field in ('language', 'ui', 'swift_version', 'dependency_manager', 'include_unit_tests',
                  'include_ui_tests', 'supports_manual_dark_mode_switch', 'generate_xcodeproj'):
        instance['sources'][field] = f'Workflow compilation fixture: {case}'
    instance['constraints'] = ['Generated fixture only; compilation does not verify product requirements.']
    config = output / '.ios-workflow/generation/project.jsonc'
    save_project_instance(config, instance)
    artifacts = output / '.ios-workflow/artifacts'
    artifacts.mkdir(parents=True)
    report = {'case': case, 'result': 'blocked', 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'validation': 'build-for-testing only; tests and App are not executed', 'exit_code': None}
    try:
        environment = {}
        for name, command in (
            ('xcode', ['xcodebuild', '-version']),
            ('sdk', ['xcodebuild', '-sdk', 'iphonesimulator', '-version', 'SDKVersion']),
            ('xcodegen', ['xcodegen', '--version']),
        ):
            value = subprocess.run(command, text=True, capture_output=True, check=True, timeout=120)
            environment[name] = value.stdout.strip()
        report['environment'] = environment
        generate_project(config, output, allow_project_records=True)
        project = generate_xcodeproj(output)
        command = [
            'xcodebuild', '-project', project.name, '-scheme', project.stem,
            '-configuration', 'Debug', '-sdk', 'iphonesimulator',
            '-destination', 'generic/platform=iOS Simulator',
            '-derivedDataPath', str(artifacts / 'DerivedData'),
            'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGNING_REQUIRED=NO', 'build-for-testing',
        ]
        report['command'] = command
        with (artifacts / 'build.log').open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=output, stdout=stream, stderr=subprocess.STDOUT,
                                    text=True, timeout=900)
        report['exit_code'] = result.returncode
        report['result'] = 'passed' if result.returncode == 0 else 'failed'
        if result.returncode:
            raise RuntimeError(f'{case}: build-for-testing failed ({result.returncode}); see {artifacts / "build.log"}')
        return report
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        raise
    finally:
        (artifacts / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=tuple(CASES), required=True)
    parser.add_argument('--output', type=Path, required=True, help='Empty temporary fixture directory')
    args = parser.parse_args()
    try:
        report = check_case(args.case, args.output.resolve())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        log = args.output / '.ios-workflow/artifacts/build.log'
        if log.is_file():
            lines = log.read_text(errors='replace').splitlines()
            errors = [line for line in lines if 'error:' in line or 'BUILD FAILED' in line or 'TEST BUILD FAILED' in line]
            print('\n'.join(errors[-20:] or lines[-20:]), file=sys.stderr)
        raise SystemExit(1)
    print(f'{args.case}: {report["result"]}; source, unit-test and UI-test targets compiled without signing')


if __name__ == '__main__':
    main()
