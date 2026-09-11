"""Run the Demo's unit and UI tests and require executed, passing xcresult evidence."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A deliberate test-suite reduction must update these reviewed minimums.
REQUIRED_BUNDLES = {'WorkflowDemoTests': 11, 'WorkflowDemoUITests': 5}


def select_device(payload: dict, runtime: str, name: str) -> dict:
    key = 'com.apple.CoreSimulator.SimRuntime.iOS-' + runtime.replace('.', '-')
    matches = [device for device in payload.get('devices', {}).get(key, [])
               if device.get('name') == name and device.get('isAvailable') is True]
    if len(matches) != 1 or not matches[0].get('udid'):
        raise RuntimeError(f'Expected one available {name} simulator on iOS {runtime}; found {len(matches)}')
    return {field: matches[0][field] for field in ('name', 'udid')} | {'runtime': runtime}


def validate_results(summary: dict, tree: dict) -> dict:
    """Reject build-only, skipped, partial or inconsistent result bundles."""
    count_fields = ('totalTestCount', 'passedTests', 'failedTests', 'skippedTests', 'expectedFailures')
    for field in count_fields:
        if type(summary.get(field)) is not int or summary[field] < 0:
            raise RuntimeError(f'Missing or invalid xcresult count: {field}')
    if (summary.get('result') != 'Passed' or summary['passedTests'] == 0
            or any(summary[field] for field in ('failedTests', 'skippedTests', 'expectedFailures'))
            or summary['totalTestCount'] != summary['passedTests']):
        raise RuntimeError('xcresult does not show all selected tests executed and passed')
    counts = {}

    def visit(node, bundle=None):
        if not isinstance(node, dict):
            raise RuntimeError('Malformed xcresult test node')
        if node.get('nodeType') in ('Unit test bundle', 'UI test bundle'):
            bundle = node.get('name')
            if not isinstance(bundle, str) or bundle in counts:
                raise RuntimeError('Missing or repeated xcresult test bundle')
            counts[bundle] = 0
        if node.get('nodeType') == 'Test Case':
            if bundle is None or node.get('result') != 'Passed':
                raise RuntimeError('xcresult contains an unexecuted or unsuccessful test case')
            counts[bundle] += 1
        for child in node.get('children', []):
            visit(child, bundle)

    for node in tree.get('testNodes', []):
        visit(node)
    for bundle, minimum in REQUIRED_BUNDLES.items():
        if counts.get(bundle, 0) < minimum:
            raise RuntimeError(f'{bundle}: requires at least {minimum} executed tests; got {counts.get(bundle, 0)}')
    if sum(counts.values()) != summary['totalTestCount']:
        raise RuntimeError('xcresult summary and test tree counts disagree')
    return {'total': summary['totalTestCount'], 'passed': summary['passedTests'],
            'failed': summary['failedTests'], 'skipped': summary['skippedTests'], 'bundles': counts}


def _capture(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, timeout=120)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise RuntimeError(f'{command[0]} failed ({result.returncode}): {detail}')
    return result.stdout.strip()


def run_demo_tests(output: Path, *, runtime: str, device_name: str,
                   expected_xcode: str | None = None) -> dict:
    output = output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError('Output must be an empty directory; prior evidence is never reused')
    output.mkdir(parents=True, exist_ok=True)
    report = {'result': 'blocked', 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'validation': 'WorkflowDemo simulator unit and UI test execution', 'exit_code': None,
              'required_minimum_tests': REQUIRED_BUNDLES, 'xcresult': 'DemoTests.xcresult'}
    try:
        for tool in ('xcodebuild', 'xcodegen', 'xcrun'):
            if not shutil.which(tool):
                raise RuntimeError(f'Required tool unavailable: {tool}')
        xcode = _capture(['xcodebuild', '-version'])
        report['environment'] = {
            'xcode': xcode, 'developer_dir': os.environ.get('DEVELOPER_DIR') or _capture(['xcode-select', '-p']),
            'sdk': _capture(['xcodebuild', '-sdk', 'iphonesimulator', '-version', 'SDKVersion']),
            'xcodegen': _capture(['xcodegen', '--version']), 'scheme': 'WorkflowDemo',
            'configuration': 'Debug', 'test_selection': 'all scheme tests; unit and UI bundles required',
        }
        if expected_xcode and xcode.splitlines()[0] != f'Xcode {expected_xcode}':
            raise RuntimeError(f'Expected Xcode {expected_xcode}; selected {xcode.splitlines()[0]}')
        device = select_device(json.loads(_capture(['xcrun', 'simctl', 'list', 'devices', 'available', '--json'])),
                               runtime, device_name)
        report['environment']['device'] = device
        destination = f'platform=iOS Simulator,id={device["udid"]}'
        report['environment']['destination'] = destination
        # Copy only current engineering inputs. Generation never touches the checkout or its records.
        project = output / 'WorkflowDemo'
        project.mkdir()
        shutil.copy2(ROOT / 'WorkflowDemo/project.yml', project / 'project.yml')
        for directory in ('App', 'Tests', 'UITests'):
            shutil.copytree(ROOT / 'WorkflowDemo' / directory, project / directory)
        _capture(['xcodegen', 'generate', '--spec', str(project / 'project.yml'), '--project', str(project)])
        command = [
            'xcodebuild', '-project', str(project / 'WorkflowDemo.xcodeproj'), '-scheme', 'WorkflowDemo',
            '-configuration', 'Debug', '-sdk', 'iphonesimulator', '-destination', destination,
            '-destination-timeout', '120', '-parallel-testing-enabled', 'NO',
            '-derivedDataPath', str(output / 'DerivedData'), '-resultBundlePath', str(output / 'DemoTests.xcresult'),
            'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGNING_REQUIRED=NO', 'test',
        ]
        report['command'] = command
        report['result'] = 'failed'
        with (output / 'test.log').open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, text=True, timeout=1200)
        report['exit_code'] = result.returncode
        result_bundle = output / 'DemoTests.xcresult'
        if not result_bundle.is_dir():
            raise RuntimeError(f'xcodebuild returned {result.returncode} without a test result bundle; see test.log')
        exported = {}
        for kind in ('summary', 'tests'):
            value = _capture(['xcrun', 'xcresulttool', 'get', 'test-results', kind,
                              '--path', str(result_bundle), '--compact'])
            (output / f'xcresult-{kind}.json').write_text(value + '\n', encoding='utf-8')
            exported[kind] = json.loads(value)
        report['observed_summary'] = {key: exported['summary'].get(key) for key in
                                      ('result', 'totalTestCount', 'passedTests', 'failedTests', 'skippedTests')}
        if result.returncode:
            raise RuntimeError(f'xcodebuild test failed ({result.returncode}); see test.log and DemoTests.xcresult')
        report['tests'] = validate_results(exported['summary'], exported['tests'])
        report['result'] = 'passed'
        return report
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        raise
    finally:
        (output / 'test-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        summary = [f'WorkflowDemo tests: **{report["result"]}**', '', report['validation'], '']
        if 'tests' in report:
            summary.extend(f'- {bundle}: {count} passed' for bundle, count in report['tests']['bundles'].items())
        if 'environment' in report:
            summary.extend(['', f'Xcode: {report["environment"]["xcode"].replace(chr(10), "; ")}'])
            if 'device' in report['environment']:
                device = report['environment']['device']
                summary.append(f'Destination: {device["name"]}, iOS {device["runtime"]}, {device["udid"]}')
        if 'error' in report:
            summary.extend(['', report['error']])
        (output / 'test-summary.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Empty explicit temporary or project artifact directory')
    parser.add_argument('--runtime', required=True, help='Exact installed iOS runtime, e.g. 18.5')
    parser.add_argument('--device-name', required=True, help='Exact available simulator name')
    parser.add_argument('--expected-xcode', help='Fail unless the selected Xcode has this exact version')
    args = parser.parse_args()
    try:
        report = run_demo_tests(args.output, runtime=args.runtime, device_name=args.device_name,
                                expected_xcode=args.expected_xcode)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        log = args.output / 'test.log'
        if log.is_file():
            lines = log.read_text(errors='replace').splitlines()
            relevant = [line for line in lines if 'error:' in line or 'failed' in line.lower()]
            print('\n'.join(relevant[-15:] or lines[-15:]), file=sys.stderr)
        raise SystemExit(1)
    print(f'WorkflowDemo: {report["tests"]["passed"]} tests passed; report: {args.output / "test-report.json"}')


if __name__ == '__main__':
    main()
