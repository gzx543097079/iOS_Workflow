import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from project_generation import (
    ConfigurationError, diagnose_project_instance, generate_project, load_jsonc,
    save_project_instance, validate_config, validate_design_tokens, validate_project_instance,
)


class ConfigurationDiagnosticsTests(unittest.TestCase):
    def example(self):
        return load_jsonc(ROOT / "distribution/project.example.jsonc")

    def test_complete_supported_instances_have_no_diagnostics(self):
        for language, ui in (("swift", "uikit"), ("swift", "swiftui"), ("objc", "uikit")):
            with self.subTest(language=language, ui=ui):
                instance = self.example()
                instance["config"].update(language=language, ui=ui)
                self.assertEqual([], diagnose_project_instance(instance))
                self.assertEqual(instance, validate_project_instance(instance))
        nimblefive = load_jsonc(ROOT / "docs/configuration-samples/nimblefive/project.json")
        self.assertEqual([], diagnose_project_instance(nimblefive))

    def test_independent_missing_unknown_enum_and_combination_errors_are_reported_together(self):
        instance = self.example()
        instance["config"].pop("bundle_id")
        instance["config"].update({"uii": "swiftui", "language": "objc", "ui": "swiftui",
                                   "architecture": "custom", "supports_dark_mode": False,
                                   "supports_manual_dark_mode_switch": True})
        errors = diagnose_project_instance(instance)
        self.assertGreaterEqual(len(errors), 5)
        text = "\n".join(errors)
        for fragment in ("config.bundle_id 缺失", "config.uii 未知字段", "config.architecture", "mvvm, mvc",
                         "config.language / config.ui", "不支持 SwiftUI", "supports_dark_mode 为 true"):
            self.assertIn(fragment, text)
        with self.assertRaises(ConfigurationError) as raised:
            validate_project_instance(instance)
        for error in errors:
            self.assertIn(error, str(raised.exception))

    def test_top_level_sources_constraints_and_token_errors_are_not_hidden_by_config_errors(self):
        instance = self.example()
        instance.pop("schema_version")
        instance["config"]["dependency_manager"] = "unknown"
        instance["mystery"] = True
        instance["sources"].pop("ui")
        instance["sources"]["new_field"] = ""
        instance["constraints"] = ["valid", None]
        instance["design_tokens"].pop("content_margin")
        instance["design_tokens"]["typo"] = 4
        instance["design_tokens"]["typography"]["body"] = "unsupported"
        text = "\n".join(diagnose_project_instance(instance))
        for fragment in ("schema_version 缺失", "mystery 未知字段", "config.dependency_manager",
                         "pod, spm, carthage, none", "sources.ui 缺失", "sources.new_field 未知字段",
                         "constraints[1]", "design_tokens.content_margin 缺失", "design_tokens.typo 未知字段",
                         "design_tokens.typography.body", "headline"):
            self.assertIn(fragment, text)

    def test_malformed_containers_and_unhashable_values_return_diagnostics(self):
        for root in (None, [], "instance", 1):
            with self.subTest(root=root):
                self.assertTrue(diagnose_project_instance(root))
                with self.assertRaises(ConfigurationError):
                    validate_project_instance(root)
        for field in ("config", "design_tokens", "sources", "constraints"):
            with self.subTest(field=field):
                instance = self.example()
                instance[field] = None
                self.assertTrue(diagnose_project_instance(instance))
        instance = self.example()
        instance["config"].update({"language": {}, "target_devices": [{}], "supported_orientations": [[]],
                                   "supported_localizations": [[]], "localization_strings": {"home.title": None}})
        instance["design_tokens"].update({"spacing": [], "typography": {"body": []}, "colors": None})
        self.assertGreaterEqual(len(diagnose_project_instance(instance)), 8)

    def test_all_supplied_scalar_types_are_checked_without_coercing_them(self):
        instance = self.example()
        instance["schema_version"] = True
        instance["config"].update({"comment_level": True, "deployment_target": 16.0, "build_number": "0",
                                   "organization_name": {}, "development_team": [], "bundle_id": None,
                                   "include_ui_tests": "false"})
        instance["design_tokens"]["spacing"]["sm"] = True
        instance["design_tokens"]["content_margin"] = float("inf")
        text = "\n".join(diagnose_project_instance(instance))
        for path in ("schema_version", "config.comment_level", "config.deployment_target", "config.build_number",
                     "config.organization_name", "config.development_team", "config.bundle_id",
                     "config.include_ui_tests", "design_tokens.spacing.sm", "design_tokens.content_margin"):
            self.assertIn(path, text)

    def test_localization_problems_are_combined_with_unrelated_invalid_fields(self):
        instance = self.example()
        instance["config"]["localization_strings"]["home.title"].pop("ru")
        instance["config"]["default_localization"] = "unlisted"
        instance["config"]["test_framework"] = "unknown"
        errors = diagnose_project_instance(instance)
        self.assertEqual(3, len(errors))
        text = "\n".join(errors)
        self.assertIn("config.localization_strings.home.title 缺少语言: ru", text)
        self.assertIn("config.default_localization", text)
        self.assertIn("xctest", text)

    def test_diagnostics_never_mutate_or_fill_missing_fields(self):
        instance = self.example()
        instance["config"].pop("ui")
        instance["design_tokens"]["colors"] = {}
        before = copy.deepcopy(instance)
        first = diagnose_project_instance(instance)
        self.assertEqual(first, diagnose_project_instance(instance))
        self.assertEqual(before, instance)
        self.assertNotIn("ui", instance["config"])
        valid = self.example()
        validated = validate_project_instance(valid)
        validated["config"]["ui"] = "changed"
        self.assertEqual("uikit", valid["config"]["ui"])

    def test_invalid_instance_is_rejected_before_creating_or_touching_project_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            instance = self.example()
            instance["config"].update(language="invalid", architecture="invalid")
            instance["config"].pop("ui")
            config_path = root / "input.json"
            config_path.write_text(json.dumps(instance), encoding="utf-8")
            output = root / "new-project"
            with self.assertRaises(ConfigurationError) as raised:
                generate_project(config_path, output)
            self.assertFalse(output.exists())
            self.assertIn("config.language", str(raised.exception))
            self.assertIn("config.architecture", str(raised.exception))
            self.assertIn("config.ui 缺失", str(raised.exception))
            records = output / ".ios-workflow"
            records.mkdir(parents=True)
            marker = records / "progress.json"
            marker.write_text('{"items": []}\n', encoding="utf-8")
            before = marker.read_bytes()
            with self.assertRaises(ConfigurationError):
                generate_project(config_path, output, allow_project_records=True)
            self.assertEqual(before, marker.read_bytes())
            self.assertEqual([records], list(output.iterdir()))
            with self.assertRaises(ConfigurationError):
                save_project_instance(root / "new-input-directory" / "project.json", instance)
            self.assertFalse((root / "new-input-directory").exists())

    def test_legacy_validation_apis_keep_their_return_and_exception_contract(self):
        instance = self.example()
        self.assertEqual(instance["config"], validate_config(instance["config"]))
        self.assertEqual(instance["design_tokens"], validate_design_tokens(instance["design_tokens"]))
        for validator in (validate_config, validate_design_tokens):
            with self.subTest(validator=validator.__name__), self.assertRaises(ConfigurationError):
                validator(None)
        config = instance["config"]
        config.update(language="objc", ui="swiftui", test_framework="invalid")
        with self.assertRaises(ConfigurationError) as raised:
            validate_config(config)
        self.assertIn("不支持 SwiftUI", str(raised.exception))
        self.assertIn("config.test_framework", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
