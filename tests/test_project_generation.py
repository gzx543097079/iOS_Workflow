import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from project_generation import ConfigurationError, generate_project, generate_xcodeproj, install_dependencies, load_jsonc, strip_jsonc, validate_config


class ProjectGenerationTests(unittest.TestCase):
    def example_config(self):
        return load_jsonc(ROOT / "distribution/project.example.jsonc")["config"]

    def write_example_config(self, directory: Path, changes):
        instance = load_jsonc(ROOT / "distribution/project.example.jsonc")
        instance["project_name"] = "Demo App"
        value = instance["config"]
        value.update(changes)
        path = directory / "example_config.jsonc"
        path.write_text(json.dumps(instance), encoding="utf-8")
        return path

    def generate(self, changes):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        example_config = self.write_example_config(root, changes)
        files = generate_project(example_config, root / "Output")
        return temporary, root / "Output", files

    def test_jsonc_preserves_comment_tokens_inside_strings(self):
        value = json.loads(strip_jsonc('{"url":"https://example.com/a/*b*/"}// comment'))
        self.assertEqual(value["url"], "https://example.com/a/*b*/")

    def test_default_config_is_valid(self):
        validated = validate_config(self.example_config())
        self.assertEqual(validated["default_language_mode"], "system")
        self.assertEqual(validated["comment_level"], 3)
        self.assertTrue(validated["supports_dark_mode"])
        self.assertFalse(validated["supports_manual_dark_mode_switch"])
        self.assertEqual(validated["localization_strings"]["home.title"]["ja"], "ホーム")

    def test_rejects_localization_key_missing_a_configured_language(self):
        config = self.example_config()
        config["localization_strings"]["home.title"].pop("ru")
        with self.assertRaisesRegex(ConfigurationError, "home.title 缺少语言: ru"):
            validate_config(config)

    def test_generates_configured_translation_for_each_language(self):
        temporary, output, _ = self.generate({
            "supported_localizations": ["zh-Hant", "es", "ja", "ar"],
            "default_localization": "es",
        })
        self.addCleanup(temporary.cleanup)
        expected = {
            "zh-Hant": '"home.title" = "首頁";',
            "es": '"home.title" = "Inicio";',
            "ja": '"home.title" = "ホーム";',
            "ar": '"home.title" = "الرئيسية";',
        }
        for locale, localized_line in expected.items():
            with self.subTest(locale=locale):
                strings = output / f"App/Resources/{locale}.lproj/Localizable.strings"
                self.assertEqual(strings.read_text().strip(), localized_line)

    def test_rejects_manual_dark_mode_switch_when_dark_mode_is_disabled(self):
        config = self.example_config()
        config.update({
            "supports_dark_mode": False,
            "supports_manual_dark_mode_switch": True,
        })
        with self.assertRaisesRegex(ConfigurationError, "只能在 supports_dark_mode 为 true 时开启"):
            validate_config(config)

    def test_rejects_objective_c_swiftui(self):
        config = self.example_config()
        config.update({"language": "objc", "ui": "swiftui"})
        with self.assertRaisesRegex(ConfigurationError, "不支持 SwiftUI"):
            validate_config(config)

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
        self.assertIn('UISceneDelegateClassName: "$(PRODUCT_MODULE_NAME).SceneDelegate"', (output / "project.yml").read_text())
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
        self.assertIn('UISceneDelegateClassName: "APPSceneDelegate"', (output / "project.yml").read_text())

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

    def test_disabling_dark_mode_forces_light_appearance(self):
        for changes, expected in (
            ({"language": "swift", "ui": "uikit"}, "UIUserInterfaceStyle: Light"),
            ({"language": "swift", "ui": "swiftui"}, "INFOPLIST_KEY_UIUserInterfaceStyle: Light"),
            ({"language": "objc", "ui": "uikit"}, "UIUserInterfaceStyle: Light"),
        ):
            with self.subTest(changes=changes):
                temporary, output, _ = self.generate({
                    **changes,
                    "supports_dark_mode": False,
                    "supports_manual_dark_mode_switch": False,
                })
                self.addCleanup(temporary.cleanup)
                self.assertIn(expected, (output / "project.yml").read_text())

    def test_generates_manual_appearance_policy_for_swift_uikit(self):
        temporary, output, _ = self.generate({"supports_manual_dark_mode_switch": True})
        self.addCleanup(temporary.cleanup)
        policy = (output / "App/Core/Appearance/AppearancePolicy.swift").read_text()
        scene = (output / "App/SceneDelegate.swift").read_text()
        self.assertIn("case system", policy)
        self.assertIn("case light", policy)
        self.assertIn("case dark", policy)
        self.assertIn("UserDefaults.standard.set", policy)
        self.assertIn("AppearancePolicy.apply(to: window)", scene)

    def test_generates_manual_appearance_policy_for_swiftui(self):
        temporary, output, _ = self.generate({
            "ui": "swiftui",
            "dependency_manager": "spm",
            "supports_manual_dark_mode_switch": True,
        })
        self.addCleanup(temporary.cleanup)
        policy = (output / "App/Core/Appearance/AppearancePolicy.swift").read_text()
        app = (output / "App/DemoAppApp.swift").read_text()
        self.assertIn("var colorScheme: ColorScheme?", policy)
        self.assertIn("@AppStorage(AppearancePolicy.storageKey)", app)
        self.assertIn(".preferredColorScheme", app)

    def test_generates_manual_appearance_policy_for_objective_c_uikit(self):
        temporary, output, _ = self.generate({
            "language": "objc",
            "dependency_manager": "carthage",
            "supports_manual_dark_mode_switch": True,
        })
        self.addCleanup(temporary.cleanup)
        policy = (output / "App/Core/Appearance/APPAppearancePolicy.m").read_text()
        scene = (output / "App/APPSceneDelegate.m").read_text()
        self.assertIn("APPAppearanceModeLight", policy)
        self.assertIn("APPAppearanceModeDark", policy)
        self.assertIn("setInteger:mode", policy)
        self.assertIn("[APPAppearancePolicy applyToWindow:self.window]", scene)

    def test_comment_level_one_omits_explanatory_comments(self):
        temporary, output, _ = self.generate({"comment_level": 1})
        self.addCleanup(temporary.cleanup)
        self.assertNotIn("//", (output / "App/Features/Home/HomeViewController.swift").read_text())
        self.assertNotIn("//", (output / "App/DesignSystem/DesignTokens.swift").read_text())

    @unittest.skipUnless(shutil.which("xcodegen"), "需要 XcodeGen")
    def test_xcodegen_accepts_all_supported_project_shapes(self):
        for changes in (
            {"language": "swift", "ui": "uikit", "supports_manual_dark_mode_switch": True},
            {"language": "swift", "ui": "swiftui", "supports_manual_dark_mode_switch": True},
            {"language": "objc", "ui": "uikit", "supports_manual_dark_mode_switch": True},
        ):
            with self.subTest(changes=changes):
                temporary, output, _ = self.generate(changes)
                self.addCleanup(temporary.cleanup)
                self.assertTrue(generate_xcodeproj(output).is_dir())

    def test_dependency_preparation_uses_expected_command(self):
        with tempfile.TemporaryDirectory() as value, patch("project_generation.shutil.which", return_value="/usr/bin/tool"), patch("project_generation.subprocess.run") as run:
            project = Path(value) / "Demo.xcodeproj"
            install_dependencies(Path(value), "spm", project)
            run.assert_called_once_with(
                ["/usr/bin/tool", "-resolvePackageDependencies", "-project", "Demo.xcodeproj"],
                cwd=Path(value), check=True, capture_output=True, text=True,
            )

    def test_refuses_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            example_config = self.write_example_config(root, {})
            output = root / "Output"
            output.mkdir()
            (output / "keep.txt").write_text("user data")
            with self.assertRaises(FileExistsError):
                generate_project(example_config, output)


if __name__ == "__main__":
    unittest.main()
