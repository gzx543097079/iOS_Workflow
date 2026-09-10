"""Exercise generation boundaries without upgrading a project's requested OS."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
from project_generation import ConfigurationError, diagnose_project_instance, generate_project, load_jsonc


class DeploymentTargetTests(unittest.TestCase):
    def instance(self, language, ui, target, manual=False):
        value = load_jsonc(ROOT / 'distribution/project.example.jsonc')
        value['config'].update(language=language, ui=ui, deployment_target=target,
                               supports_manual_dark_mode_switch=manual)
        return value

    def test_unsupported_targets_fail_before_writing_and_preserve_requested_value(self):
        for language, ui, targets in (
            ('swift', 'uikit', ('1.0', '12.0', '12.9')),
            ('objc', 'uikit', ('1.0', '12.9')),
            ('swift', 'swiftui', ('1.0', '12.0', '13.0', '13.9')),
        ):
            for target in targets:
                for manual in (False, True):
                    with self.subTest(language=language, ui=ui, target=target, manual=manual), tempfile.TemporaryDirectory() as name:
                        value = self.instance(language, ui, target, manual)
                        original = copy.deepcopy(value)
                        errors = diagnose_project_instance(value)
                        self.assertTrue(any('config.deployment_target' in error for error in errors))
                        self.assertEqual(original, value)
                        source = Path(name) / 'project.json'
                        source.write_text(json.dumps(value))
                        output = Path(name) / 'App'
                        with self.assertRaises(ConfigurationError):
                            generate_project(source, output)
                        self.assertFalse(output.exists())
                        self.assertEqual(original, json.loads(source.read_text()))

    def test_boundary_and_higher_targets_are_preserved_in_generated_projects(self):
        for language, ui, minimum in (('swift', 'uikit', '13.0'), ('objc', 'uikit', '13.0'), ('swift', 'swiftui', '14.0')):
            for target in (minimum, '16.0'):
                for mode in ('5', '6'):
                    with self.subTest(language=language, ui=ui, target=target, mode=mode), tempfile.TemporaryDirectory() as name:
                        value = self.instance(language, ui, target, manual=True)
                        value['config']['swift_version'] = mode
                        self.assertEqual([], diagnose_project_instance(value))
                        source = Path(name) / 'project.json'
                        source.write_text(json.dumps(value))
                        output = Path(name) / 'App'
                        generate_project(source, output)
                        self.assertIn(f'iOS: "{target}"', (output / 'project.yml').read_text())

    def test_missing_or_malformed_target_is_not_filled_and_other_diagnostics_remain(self):
        for target in (None, 13, '13', '13.0.0', 'invalid'):
            value = self.instance('swift', 'swiftui', target)
            errors = diagnose_project_instance(value)
            self.assertTrue(any('config.deployment_target' in error for error in errors))
            self.assertEqual(target, value['config']['deployment_target'])
        value = self.instance('swift', 'swiftui', '13.0')
        value['config']['swift_version'] = '5.10'
        errors = diagnose_project_instance(value)
        self.assertTrue(any('config.deployment_target' in error for error in errors))
        self.assertTrue(any('config.swift_version' in error for error in errors))
        del value['config']['deployment_target']
        self.assertTrue(any('deployment_target' in error for error in diagnose_project_instance(value)))
        self.assertNotIn('deployment_target', value['config'])

    def test_invalid_language_types_are_diagnosed_without_boundary_lookup_crashing(self):
        for language, ui in (([], 'uikit'), ('swift', {}), ('objc', 'swiftui')):
            value = self.instance(language, ui, '1.0')
            self.assertTrue(diagnose_project_instance(value))


if __name__ == '__main__':
    unittest.main()
