"""Generation must not escape its destination or overwrite concurrent files."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
import project_generation as generation


class GenerationPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.instance = generation.load_jsonc(ROOT / 'distribution/project.example.jsonc')

    def configure_locale(self, locale):
        config = self.instance['config']
        config['supported_localizations'] = [locale]
        config['default_localization'] = locale
        config['localization_strings'] = {'home.title': {locale: 'Home'}}
        path = self.root / 'input.json'
        path.write_text(json.dumps(self.instance))
        return path

    def test_traversal_configuration_is_rejected_before_any_generation(self):
        marker = self.root / 'outside.lproj/Localizable.strings'
        marker.parent.mkdir()
        marker.write_text('existing user content')
        source = self.configure_locale('../../../outside')
        with self.assertRaises(generation.ConfigurationError):
            generation.generate_project(source, self.root / 'Output')
        self.assertFalse((self.root / 'Output').exists())
        self.assertEqual('existing user content', marker.read_text())

    def test_path_like_and_duplicate_language_identifiers_are_rejected(self):
        for locale in ('/en', '../en', r'C:\en', 'en_US', 'en/GB', 'en\x00', ' en', 'en..', 'en-'):
            with self.subTest(locale=locale):
                self.configure_locale(locale)
                errors = generation.diagnose_project_instance(self.instance)
                self.assertTrue(any('supported_localizations' in error for error in errors))
        self.configure_locale('en')
        self.instance['config']['supported_localizations'] = ['en', 'EN']
        self.instance['config']['localization_strings']['home.title']['EN'] = 'Home'
        self.assertTrue(any('重复' in error for error in generation.diagnose_project_instance(self.instance)))

    def test_supported_language_tag_shapes_stay_usable(self):
        for locale in ('en', 'zh-Hans', 'pt-BR', 'es-419', 'sr-Latn-RS'):
            with self.subTest(locale=locale):
                self.configure_locale(locale)
                self.assertEqual([], generation.diagnose_project_instance(self.instance))

    def test_entire_render_plan_is_checked_before_creating_files(self):
        for invalid in ('../outside.txt', '/outside.txt', r'C:\outside.txt', '.agents/keep.md', 'App/../outside.txt'):
            with self.subTest(invalid=invalid):
                output = self.root / 'Output'
                with self.assertRaises(generation.ConfigurationError):
                    generation._write_generated_sources(output, {'App/good.swift': 'safe', invalid: 'bad'})
                self.assertFalse(output.exists())
        with self.assertRaises(generation.ConfigurationError):
            generation._write_generated_sources(self.root / 'Output', {'App/en.txt': 'a', 'App/EN.txt': 'b'})

    def test_symlinked_subdirectory_is_never_followed(self):
        output, outside = self.root / 'Output', self.root / 'Outside'
        output.mkdir()
        outside.mkdir()
        (output / 'App').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(generation.ConfigurationError):
            generation._write_generated_sources(output, {'App/value.swift': 'new'})
        self.assertEqual([], list(outside.iterdir()))

    def test_file_created_after_preflight_is_not_overwritten(self):
        output = self.root / 'Output'
        original = generation._validate_output_paths
        def race(root, sources):
            original(root, sources)
            root.mkdir()
            (root / 'value.swift').write_text('concurrent user file')
        with patch.object(generation, '_validate_output_paths', side_effect=race):
            with self.assertRaises(FileExistsError):
                generation._write_generated_sources(output, {'value.swift': 'generated'})
        self.assertEqual('concurrent user file', (output / 'value.swift').read_text())

    def test_symlink_created_after_preflight_cannot_redirect_writes(self):
        output, outside = self.root / 'Output', self.root / 'Outside'
        outside.mkdir()
        original = generation._validate_output_paths
        def race(root, sources):
            original(root, sources)
            root.mkdir()
            (root / 'App').symlink_to(outside, target_is_directory=True)
        with patch.object(generation, '_validate_output_paths', side_effect=race):
            with self.assertRaises(OSError):
                generation._write_generated_sources(output, {'App/value.swift': 'generated'})
        self.assertEqual([], list(outside.iterdir()))


if __name__ == '__main__':
    unittest.main()
