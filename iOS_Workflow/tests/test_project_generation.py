import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.project_generation import ConfigurationError, generate_project, generate_xcodeproj, install_dependencies, load_jsonc, strip_jsonc, validate_defaults


ROOT = Path(__file__).resolve().parents[1]


class ProjectGenerationTests(unittest.TestCase):
    def defaults(self):
        return load_jsonc(ROOT / "config/defaults.jsonc")

    def write_defaults(self, directory: Path, changes):
        value = self.defaults()
        value.update(changes)
        path = directory / "defaults.jsonc"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def generate(self, changes):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        defaults = self.write_defaults(root, changes)
        files = generate_project(defaults, ROOT / "config/design-tokens.jsonc", root / "Output", "Demo App")
        return temporary, root / "Output", files

    def test_jsonc_preserves_comment_tokens_inside_strings(self):
        value = json.loads(strip_jsonc('{"url":"https://example.com/a/*b*/"}// comment'))
        self.assertEqual(value["url"], "https://example.com/a/*b*/")

    def test_default_config_is_valid(self):
        validated = validate_defaults(self.defaults())
        self.assertEqual(validated["default_language_mode"], "system")
        self.assertEqual(validated["comment_level"], 3)

    def test_rejects_objective_c_swiftui(self):
        config = self.defaults()
        config.update({"language": "objc", "ui": "swiftui"})
        with self.assertRaisesRegex(ConfigurationError, "不支持 SwiftUI"):
            validate_defaults(config)

    def test_generates_swift_uikit_project(self):
        temporary, output, files = self.generate({"language": "swift", "ui": "uikit", "dependency_manager": "pod"})
        self.addCleanup(temporary.cleanup)
        self.assertTrue((output / "App/AppDelegate.swift").is_file())
        self.assertTrue((output / "App/DesignSystem/DesignTokens.swift").is_file())
        self.assertTrue((output / "Podfile").is_file())
        self.assertTrue((output / "App/Features/Home/HomeViewModel.swift").is_file())
        self.assertIn('mode = "system"', (output / "App/Core/Localization/LocalizationPolicy.swift").read_text())
        self.assertIn("SWIFT_STRICT_CONCURRENCY: complete", (output / "project.yml").read_text())
        self.assertIn("PRODUCT_MODULE_NAME: DemoAppAppModule", (output / "project.yml").read_text())
        self.assertIn("业务模块的入口", (output / "App/Features/Home/HomeViewController.swift").read_text())
        self.assertGreater(len(files), 10)

    def test_generates_swiftui_project(self):
        temporary, output, _ = self.generate({"language": "swift", "ui": "swiftui", "dependency_manager": "spm"})
        self.addCleanup(temporary.cleanup)
        self.assertTrue((output / "App/DemoAppApp.swift").is_file())
        self.assertIn("NavigationView", (output / "App/Features/Home/HomeView.swift").read_text())
        self.assertNotIn("NavigationStack", (output / "App/Features/Home/HomeView.swift").read_text())
        self.assertIn("Color(UIColor.systemBlue)", (output / "App/DesignSystem/DesignTokens.swift").read_text())
        self.assertNotIn("Podfile", {path.name for path in output.iterdir()})

    def test_generates_objective_c_uikit_project(self):
        temporary, output, _ = self.generate({"language": "objc", "ui": "uikit", "dependency_manager": "carthage"})
        self.addCleanup(temporary.cleanup)
        self.assertTrue((output / "App/main.m").is_file())
        self.assertTrue((output / "App/DesignSystem/DesignTokens.h").is_file())
        self.assertTrue((output / "App/DesignSystem/DesignTokens.m").is_file())
        objc_tokens = (output / "App/DesignSystem/DesignTokens.m").read_text()
        self.assertIn("contentMaxWidth", objc_tokens)
        self.assertIn("borderWidthHairline", objc_tokens)
        self.assertIn("animationDurationQuick", objc_tokens)
        self.assertIn("typographyTitle", objc_tokens)
        self.assertTrue((output / "App/Features/Home/APPHomeViewModel.h").is_file())
        self.assertTrue((output / "App/Core/Localization/APPLocalizationPolicy.m").is_file())
        self.assertTrue((output / "Cartfile").is_file())

    def test_honors_fixed_language_mvc_navigation_and_ui_tests(self):
        temporary, output, _ = self.generate({
            "architecture": "mvc",
            "navigation_enabled": False,
            "default_language_mode": "fixed",
            "default_localization": "zh-Hans",
            "include_ui_tests": True,
        })
        self.addCleanup(temporary.cleanup)
        self.assertFalse((output / "App/Features/Home/HomeViewModel.swift").exists())
        self.assertNotIn("UINavigationController", (output / "App/SceneDelegate.swift").read_text())
        self.assertIn('mode = "fixed"', (output / "App/Core/Localization/LocalizationPolicy.swift").read_text())
        self.assertIn('defaultLocalization = "zh-Hans"', (output / "App/Core/Localization/LocalizationPolicy.swift").read_text())
        self.assertTrue((output / "UITests/DemoAppUITests.swift").is_file())

    def test_comment_level_one_omits_explanatory_comments(self):
        temporary, output, _ = self.generate({"comment_level": 1})
        self.addCleanup(temporary.cleanup)
        self.assertNotIn("//", (output / "App/Features/Home/HomeViewController.swift").read_text())
        self.assertNotIn("//", (output / "App/DesignSystem/DesignTokens.swift").read_text())

    @unittest.skipUnless(shutil.which("xcodegen"), "需要 XcodeGen")
    def test_xcodegen_accepts_all_supported_project_shapes(self):
        for changes in (
            {"language": "swift", "ui": "uikit"},
            {"language": "swift", "ui": "swiftui"},
            {"language": "objc", "ui": "uikit"},
        ):
            with self.subTest(changes=changes):
                temporary, output, _ = self.generate(changes)
                self.addCleanup(temporary.cleanup)
                self.assertTrue(generate_xcodeproj(output).is_dir())

    def test_dependency_preparation_uses_expected_command(self):
        with tempfile.TemporaryDirectory() as value, patch("tools.project_generation.shutil.which", return_value="/usr/bin/tool"), patch("tools.project_generation.subprocess.run") as run:
            project = Path(value) / "Demo.xcodeproj"
            install_dependencies(Path(value), "spm", project)
            run.assert_called_once_with(
                ["/usr/bin/tool", "-resolvePackageDependencies", "-project", "Demo.xcodeproj"],
                cwd=Path(value), check=True, capture_output=True, text=True,
            )

    def test_refuses_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            defaults = self.write_defaults(root, {})
            output = root / "Output"
            output.mkdir()
            (output / "keep.txt").write_text("user data")
            with self.assertRaises(FileExistsError):
                generate_project(defaults, ROOT / "config/design-tokens.jsonc", output, "Demo")


if __name__ == "__main__":
    unittest.main()
