import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/ios-workflow'
sys.path.insert(0, str(SKILL / 'scripts'))
from project_generation import (ConfigurationError, validate_project_instance,
    load_project_instance, save_project_instance, generate_project, materialize_project)


class ProjectInstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.template = ROOT / 'distribution/project.example.jsonc'
        self.example = ROOT / 'docs/configuration-samples/nimblefive/project.json'

    def create(self, overrides=None):
        instance = load_project_instance(self.template)
        instance['project_name'] = 'Example'
        instance['config'].update(overrides or {})
        return validate_project_instance(instance)

    def test_explicit_example_copy_and_projects_are_isolated(self):
        one = self.create({'ui': 'swiftui', 'supported_localizations': ['en']})
        two = self.create()
        self.assertEqual(two['config']['ui'], 'uikit')
        self.assertEqual(one['config']['supported_localizations'], ['en'])
        path = self.root / 'project.json'
        save_project_instance(path, one)
        # Loading an existing instance must not touch shared files.
        import project_generation as module
        original = module.load_jsonc
        with patch.object(module, 'load_jsonc', side_effect=lambda p: original(p) if p == path else self.fail('read shared defaults')):
            self.assertEqual(load_project_instance(path), one)
        one['design_tokens']['spacing']['sm'] = 99
        self.assertEqual(two['design_tokens']['spacing']['sm'], 8)

    def test_rejects_invalid_overrides_without_saving(self):
        for change in [{'ui': 'swfitui'}, {'unknown': True},
                       {'language': 'objc', 'ui': 'swiftui'},
                       {'supported_orientations': ['diagonal']},
                       {'supported_localizations': ['xx']}]:
            with self.subTest(change=change), self.assertRaises(ConfigurationError):
                self.create(change)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_snapshot_version_missing_field_and_typo_rejected_before_output(self):
        base = load_project_instance(self.example)
        cases = [copy.deepcopy(base) for _ in range(3)]
        cases[0]['schema_version'] = 2
        cases[1]['config'].pop('ui')
        cases[2]['config']['orienation'] = 'portrait'
        for instance in cases:
            path = self.root / 'bad.json'
            path.write_text(json.dumps(instance))
            with self.assertRaises(ConfigurationError):
                generate_project(path, self.root / 'Output')
            self.assertFalse((self.root / 'Output').exists())

    def test_saving_does_not_overwrite_project_instance(self):
        path = self.root / 'project.json'
        save_project_instance(path, self.create())
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            save_project_instance(path, self.create({'ui': 'swiftui'}))
        self.assertEqual(path.read_bytes(), before)

    def test_nimblefive_snapshot_drives_generation_without_shared_files(self):
        out = self.root / 'Output'
        generate_project(self.example, out)
        self.assertFalse((out / '.ios-workflow/project.json').exists())
        self.assertFalse((out / 'workflow.json').exists())
        yml = (out / 'project.yml').read_text()
        for value in ['iOS: "16.0"', 'TARGETED_DEVICE_FAMILY: "1"', 'UIInterfaceOrientationPortrait',
                      'com.gengzhixiang.nimblefive', 'NimbleFiveUITests']:
            self.assertIn(value, yml)
        self.assertTrue((out / 'App/Features/Home/HomeView.swift').exists())
        self.assertEqual([p.name for p in (out / 'App/Resources').glob('*.lproj')], ['en.lproj'])

    def test_uikit_orientation_and_project_name_guard(self):
        path = self.root / 'project.json'
        save_project_instance(path, self.create({'supported_orientations': ['portrait']}))
        with self.assertRaises(ConfigurationError):
            generate_project(self.root / 'missing.json', self.root / 'Wrong')
        self.assertFalse((self.root / 'Wrong').exists())
        out = self.root / 'Output'
        generate_project(path, out)
        self.assertIn('UISupportedInterfaceOrientations: [UIInterfaceOrientationPortrait]', (out / 'project.yml').read_text())

    def test_materialize_uses_instance_dependency_choice(self):
        path = self.root / 'project.json'
        save_project_instance(path, self.create({'dependency_manager': 'none', 'generate_xcodeproj': False}))
        result = materialize_project(path, self.root / 'Output')
        self.assertIsNone(result['project'])
        self.assertFalse((self.root / 'Output/Podfile').exists())
