"""A green Demo check requires unit and UI execution evidence, not a successful build."""
import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('demo_test_check', ROOT / 'scripts/check_demo_tests.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def result_fixture():
    bundles = []
    for name, count in check.REQUIRED_BUNDLES.items():
        bundles.append({'name': name, 'nodeType': 'UI test bundle' if 'UI' in name else 'Unit test bundle',
                        'children': [{'nodeType': 'Test Case', 'name': f'test{number}()', 'result': 'Passed'}
                                     for number in range(count)]})
    total = sum(check.REQUIRED_BUNDLES.values())
    return ({'result': 'Passed', 'totalTestCount': total, 'passedTests': total, 'failedTests': 0,
             'skippedTests': 0, 'expectedFailures': 0},
            {'testNodes': [{'nodeType': 'Test Plan', 'children': bundles}]})


class DemoResultValidationTests(unittest.TestCase):
    def test_real_case_counts_are_reported_for_both_bundles(self):
        summary, tree = result_fixture()
        self.assertEqual({'total': 16, 'passed': 16, 'failed': 0, 'skipped': 0,
                          'bundles': {'WorkflowDemoTests': 11, 'WorkflowDemoUITests': 5}},
                         check.validate_results(summary, tree))

    def test_green_build_or_partial_test_results_cannot_pass(self):
        summary, tree = result_fixture()
        mutations = [dict(summary, totalTestCount=0, passedTests=0),
                     dict(summary, skippedTests=1), dict(summary, failedTests=1),
                     dict(summary, expectedFailures=1), dict(summary, passedTests=True),
                     dict(summary, totalTestCount=15), dict(summary, result='Failed'), {}]
        for invalid in mutations:
            with self.subTest(summary=invalid), self.assertRaises(RuntimeError):
                check.validate_results(invalid, tree)
        for bundle_to_remove in (0, 1):
            partial = copy.deepcopy(tree)
            del partial['testNodes'][0]['children'][bundle_to_remove]
            with self.subTest(missing_bundle=bundle_to_remove), self.assertRaises(RuntimeError):
                check.validate_results(summary, partial)

    def test_tree_failures_and_count_mismatch_override_summary(self):
        summary, tree = result_fixture()
        mutations = []
        failed = copy.deepcopy(tree)
        failed['testNodes'][0]['children'][1]['children'][0]['result'] = 'Skipped'
        mutations.append(failed)
        extra = copy.deepcopy(tree)
        extra['testNodes'][0]['children'][0]['children'].append({'nodeType': 'Test Case', 'result': 'Passed'})
        mutations.append(extra)
        duplicate = copy.deepcopy(tree)
        duplicate['testNodes'][0]['children'].append(copy.deepcopy(duplicate['testNodes'][0]['children'][0]))
        mutations.append(duplicate)
        mutations.append({'testNodes': []})
        for invalid in mutations:
            with self.subTest(tree=invalid), self.assertRaises(RuntimeError):
                check.validate_results(summary, invalid)

    def test_device_selection_never_falls_back_to_a_different_runtime(self):
        device = {'name': 'iPhone 16 Pro', 'udid': 'fixture-id', 'isAvailable': True}
        payload = {'devices': {'com.apple.CoreSimulator.SimRuntime.iOS-18-5': [device]}}
        self.assertEqual('fixture-id', check.select_device(payload, '18.5', 'iPhone 16 Pro')['udid'])
        with self.assertRaises(RuntimeError):
            check.select_device(payload, '18.4', 'iPhone 16 Pro')
        payload['devices']['com.apple.CoreSimulator.SimRuntime.iOS-18-5'].append(dict(device))
        with self.assertRaises(RuntimeError):
            check.select_device(payload, '18.5', 'iPhone 16 Pro')


class DemoExecutionTests(unittest.TestCase):
    def fixture_run(self, output, *, exit_code=0, create_bundle=True, wrong_xcode=False):
        summary, tree = result_fixture()
        commands = []

        def execute(command, **kwargs):
            commands.append(command)
            if command[-1] == 'test':
                if create_bundle:
                    (output / 'DemoTests.xcresult').mkdir()
                kwargs['stdout'].write('fixture test execution\n')
                return subprocess.CompletedProcess(command, exit_code)
            if command == ['xcodebuild', '-version']:
                text = 'Xcode 16.3\nBuild version fixture' if wrong_xcode else 'Xcode 16.4\nBuild version fixture'
            elif command[:3] == ['xcrun', 'simctl', 'list']:
                text = json.dumps({'devices': {'com.apple.CoreSimulator.SimRuntime.iOS-18-5': [
                    {'name': 'iPhone 16 Pro', 'udid': 'fixture-id', 'isAvailable': True}]}})
            elif 'test-results' in command:
                text = json.dumps(summary if command[4] == 'summary' else tree)
            else:
                text = 'fixture tool version'
            return subprocess.CompletedProcess(command, 0, stdout=text, stderr='')

        with patch.object(check.shutil, 'which', return_value='/fixture/tool'), \
             patch.object(check.subprocess, 'run', side_effect=execute):
            if exit_code or not create_bundle or wrong_xcode:
                with self.assertRaises(RuntimeError):
                    check.run_demo_tests(output, runtime='18.5', device_name='iPhone 16 Pro', expected_xcode='16.4')
            else:
                check.run_demo_tests(output, runtime='18.5', device_name='iPhone 16 Pro', expected_xcode='16.4')
        return commands, json.loads((output / 'test-report.json').read_text())

    def test_executes_test_action_with_explicit_destination_and_new_result_bundle(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name)
            commands, report = self.fixture_run(output)
            command = next(command for command in commands if command[-1] == 'test')
            self.assertIn('platform=iOS Simulator,id=fixture-id', command)
            self.assertIn('CODE_SIGNING_ALLOWED=NO', command)
            self.assertIn(str(output.resolve() / 'DemoTests.xcresult'), command)
            self.assertFalse(any('build-for-testing' in command for command in commands))
            self.assertEqual('passed', report['result'])
            self.assertEqual(16, report['tests']['passed'])
            self.assertTrue((output / 'WorkflowDemo/project.yml').is_file())
            self.assertFalse((output / 'WorkflowDemo/.ios-workflow').exists())
            self.assertTrue((output / 'test-summary.md').is_file())

    def test_nonzero_exit_or_missing_result_bundle_fails_with_report(self):
        for options in ({'exit_code': 65}, {'create_bundle': False}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as name:
                _, report = self.fixture_run(Path(name), **options)
                self.assertEqual('failed', report['result'])
                self.assertIn('error', report)

    def test_wrong_toolchain_is_blocked_before_tests_run(self):
        with tempfile.TemporaryDirectory() as name:
            commands, report = self.fixture_run(Path(name), wrong_xcode=True)
            self.assertEqual('blocked', report['result'])
            self.assertIsNone(report['exit_code'])
            self.assertFalse(any(command[-1] == 'test' for command in commands))

    def test_previous_evidence_and_missing_tools_cannot_produce_success(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name)
            with patch.object(check.shutil, 'which', return_value=None), self.assertRaises(RuntimeError):
                check.run_demo_tests(output, runtime='18.5', device_name='iPhone 16 Pro')
            old_report = (output / 'test-report.json').read_text()
            self.assertEqual('blocked', json.loads(old_report)['result'])
            with self.assertRaises(FileExistsError):
                check.run_demo_tests(output, runtime='18.5', device_name='iPhone 16 Pro')
            self.assertEqual(old_report, (output / 'test-report.json').read_text())


if __name__ == '__main__':
    unittest.main()
