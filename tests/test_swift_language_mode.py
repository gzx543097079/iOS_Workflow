import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
from project_generation import ConfigurationError, diagnose_project_instance, generate_project, load_jsonc


class SwiftLanguageModeTests(unittest.TestCase):
    def test_toolchain_versions_and_non_string_modes_fail_before_generation(self):
        for mode in ('5.10', '6.0', '5.0', '4.2', 5, None):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                instance = load_jsonc(ROOT / 'distribution/project.example.jsonc')
                instance['config']['swift_version'] = mode
                self.assertTrue(any('swift_version' in error for error in diagnose_project_instance(instance)))
                source = root / 'input.json'
                source.write_text(json.dumps(instance))
                with self.assertRaises(ConfigurationError):
                    generate_project(source, root / 'Project')
                self.assertFalse((root / 'Project').exists())

    def test_each_supported_mode_reaches_the_actual_generated_build_setting(self):
        for mode in ('5', '6'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                instance = load_jsonc(ROOT / 'distribution/project.example.jsonc')
                instance['config']['swift_version'] = mode
                source = root / 'input.json'
                source.write_text(json.dumps(instance))
                generate_project(source, root / 'Project')
                self.assertIn(f'SWIFT_VERSION: "{mode}"', (root / 'Project/project.yml').read_text())

    def test_published_and_nimblefive_examples_have_explicit_language_modes(self):
        for path in ('distribution/project.example.jsonc', 'docs/configuration-samples/nimblefive/project.json'):
            with self.subTest(path=path):
                instance = load_jsonc(ROOT / path)
                self.assertEqual([], diagnose_project_instance(instance))
                self.assertEqual('5', instance['config']['swift_version'])
                self.assertIn('语言模式', instance['sources']['swift_version'])


if __name__ == '__main__':
    unittest.main()
