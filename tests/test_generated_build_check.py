"""The release compiler check must execute a build and propagate real exit status."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('generated_build_check', ROOT / 'scripts/check_generated_projects.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class GeneratedBuildCheckTests(unittest.TestCase):
    def run_fixture(self, directory, code):
        commands = []
        def execute(command, **kwargs):
            commands.append(command)
            if command[-1] == 'build-for-testing':
                kwargs['stdout'].write('fixture execution result\n')
                return subprocess.CompletedProcess(command, code)
            return subprocess.CompletedProcess(command, 0, stdout='fixture tool version\n')
        with patch.object(check.shutil, 'which', return_value='/fixture/tool'), \
             patch.object(check.subprocess, 'run', side_effect=execute), \
             patch.object(check, 'generate_xcodeproj', return_value=directory / 'WorkflowBuildFixture.xcodeproj'):
            if code:
                with self.assertRaises(RuntimeError):
                    check.check_case('swift-uikit-5', directory)
            else:
                check.check_case('swift-uikit-5', directory)
        return commands, json.loads((directory / '.ios-workflow/artifacts/build-report.json').read_text())

    def test_success_requires_build_execution_and_reports_compilation_only(self):
        with tempfile.TemporaryDirectory() as name:
            commands, report = self.run_fixture(Path(name), 0)
            build = commands[-1]
            self.assertEqual('build-for-testing', build[-1])
            self.assertIn('CODE_SIGNING_ALLOWED=NO', build)
            self.assertIn('generic/platform=iOS Simulator', build)
            self.assertEqual(0, report['exit_code'])
            self.assertEqual('passed', report['result'])
            self.assertIn('not executed', report['validation'])
            config = json.loads((Path(name) / '.ios-workflow/generation/project.jsonc').read_text())['config']
            self.assertTrue(config['include_unit_tests'])
            self.assertTrue(config['include_ui_tests'])
            self.assertEqual('none', config['dependency_manager'])

    def test_compiler_failure_fails_the_check_and_preserves_diagnostics(self):
        with tempfile.TemporaryDirectory() as name:
            _, report = self.run_fixture(Path(name), 65)
            self.assertEqual('failed', report['result'])
            self.assertEqual(65, report['exit_code'])
            self.assertIn('build-for-testing failed', report['error'])
            self.assertTrue((Path(name) / '.ios-workflow/artifacts/build.log').is_file())

    def test_missing_tools_or_existing_results_cannot_be_reported_as_passed(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / 'Output'
            with patch.object(check.shutil, 'which', return_value=None), self.assertRaises(RuntimeError):
                check.check_case('swiftui-5', output)
            self.assertFalse(output.exists())
            output.mkdir()
            (output / 'keep').write_text('previous result')
            with self.assertRaises(FileExistsError):
                check.check_case('swiftui-5', output)
            self.assertEqual('previous result', (output / 'keep').read_text())


if __name__ == '__main__':
    unittest.main()
