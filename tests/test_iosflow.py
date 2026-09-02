import importlib.machinery
import importlib.util
import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "iosflow"
loader = importlib.machinery.SourceFileLoader("iosflow", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
iosflow = importlib.util.module_from_spec(spec)
loader.exec_module(iosflow)


class GeneratorTests(unittest.TestCase):
    def args(self, output, language, ui, architecture):
        return SimpleNamespace(
            name="Sample App",
            language=language,
            ui=ui,
            architecture=architecture,
            navigation_enabled=None,
            dependency_manager=None,
            bundle_id_prefix="com.example",
            deployment_target="17.0",
            objc_prefix="APP",
            output=output,
            no_xcodegen=True,
            force=False,
        )

    def test_supported_matrix_generates_project(self):
        matrix = [
            ("swift", "swiftui", "mvvm"),
            ("swift", "swiftui", "mvc"),
            ("swift", "uikit", "mvvm"),
            ("swift", "uikit", "mvc"),
            ("objc", "uikit", "mvvm"),
            ("objc", "uikit", "mvc"),
        ]
        for index, combination in enumerate(matrix):
            with self.subTest(combination=combination), tempfile.TemporaryDirectory() as temp:
                args = self.args(temp, *combination)
                args.name = f"Sample App {chr(65 + index)}"
                iosflow.generate_project(args)
                project = Path(temp) / f"SampleApp{chr(65 + index)}"
                self.assertTrue((project / "project.yml").exists())
                self.assertTrue((project / "Standards" / "code-style.md").exists())
                self.assertTrue((project / "Resources" / "PrivacyInfo.xcprivacy").exists())
                self.assertTrue((project / "Resources" / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json").exists())
                self.assertTrue((project / "Tests").exists())
                with (project / "Resources" / "Info.plist").open("rb") as plist_file:
                    info = plistlib.load(plist_file)
                self.assertEqual(info["CFBundleIdentifier"], "$(PRODUCT_BUNDLE_IDENTIFIER)")
                self.assertEqual(info["CFBundleExecutable"], "$(EXECUTABLE_NAME)")
                self.assertEqual(info["CFBundlePackageType"], "$(PRODUCT_BUNDLE_PACKAGE_TYPE)")
                self.assertEqual(info["CFBundleShortVersionString"], "$(MARKETING_VERSION)")
                self.assertEqual(info["CFBundleVersion"], "$(CURRENT_PROJECT_VERSION)")
                project_spec = (project / "project.yml").read_text(encoding="utf-8")
                self.assertIn('MARKETING_VERSION: "1.0"', project_spec)
                self.assertIn("ORGANIZATIONNAME: \"Test Team\"", project_spec)
                self.assertNotIn("XCODE_VERSION", project_spec)
                self.assertNotIn(f"  base:\n    PRODUCT_NAME: {project.name}", project_spec)
                self.assertIn(f"      base:\n        PRODUCT_NAME: {project.name}", project_spec)
                self.assertIn("      - path: Resources\n        excludes:\n          - Info.plist", project_spec)

    def test_rejects_objc_swiftui(self):
        options = iosflow.load_defaults()
        options.update({"language": "objc", "ui": "swiftui", "architecture": "mvvm"})
        with self.assertRaises(iosflow.WorkflowError):
            iosflow.validate_options(options)

    def test_jsonc_comments_do_not_modify_strings(self):
        content = '{"url": "https://example.com", // comment\n"enabled": true}'
        parsed = iosflow.json.loads(iosflow.strip_jsonc_comments(content))
        self.assertEqual(parsed["url"], "https://example.com")

    def test_defaults_do_not_pin_xcode_version(self):
        defaults = iosflow.load_defaults()
        self.assertNotIn("xcode_version", defaults)

    def test_navigation_defaults_to_enabled(self):
        self.assertTrue(iosflow.load_defaults()["navigation_enabled"])

    def test_dependency_manager_defaults_to_pod(self):
        self.assertEqual(iosflow.load_defaults()["dependency_manager"], "pod")

    def test_defaults_include_common_global_localizations(self):
        expected = {
            "zh-Hans", "zh-Hant", "en", "es", "fr", "de",
            "ja", "ko", "pt-BR", "it", "ar", "ru",
        }
        self.assertTrue(expected.issubset(iosflow.load_defaults()["supported_localizations"]))

    def test_default_localization_is_english(self):
        self.assertEqual(iosflow.load_defaults()["default_localization"], "en")

    def test_generated_localizations_use_translated_home_titles(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.args(temp, "swift", "uikit", "mvvm")
            args.name = "LocalizedApp"
            iosflow.generate_project(args)
            resources = Path(temp) / "LocalizedApp" / "Resources"
            expected = {
                "en": '"home.title" = "Home";',
                "es": '"home.title" = "Inicio";',
                "ja": '"home.title" = "ホーム";',
                "pt-BR": '"home.title" = "Início";',
                "ar": '"home.title" = "الرئيسية";',
            }
            for localization, content in expected.items():
                with self.subTest(localization=localization):
                    strings = resources / f"{localization}.lproj" / "Localizable.strings"
                    self.assertEqual(strings.read_text(encoding="utf-8").strip(), content)

    def test_dependency_manager_generates_matching_files(self):
        combinations = (
            ("pod", "Podfile", "target 'DependencyApp' do"),
            ("carthage", "Cartfile", 'github "Alamofire/Alamofire"'),
        )
        for manager, filename, expected in combinations:
            with self.subTest(manager=manager), tempfile.TemporaryDirectory() as temp:
                args = self.args(temp, "swift", "uikit", "mvvm")
                args.name = "DependencyApp"
                args.dependency_manager = manager
                iosflow.generate_project(args)
                content = (Path(temp) / "DependencyApp" / filename).read_text(encoding="utf-8")
                self.assertIn(expected, content)

    def test_spm_and_none_do_not_generate_external_manager_files(self):
        for manager in ("spm", "none"):
            with self.subTest(manager=manager), tempfile.TemporaryDirectory() as temp:
                args = self.args(temp, "swift", "swiftui", "mvvm")
                args.name = "DependencyApp"
                args.dependency_manager = manager
                iosflow.generate_project(args)
                project = Path(temp) / "DependencyApp"
                self.assertFalse((project / "Podfile").exists())
                self.assertFalse((project / "Cartfile").exists())

    def test_rejects_unsupported_dependency_manager(self):
        options = iosflow.load_defaults()
        options["dependency_manager"] = "unknown"
        with self.assertRaises(iosflow.WorkflowError):
            iosflow.validate_options(options)

    def test_no_navigation_removes_navigation_containers(self):
        combinations = [
            ("SwiftUINoNavigation", "swift", "swiftui", "Sources/Features/Home/HomeView.swift"),
            ("UIKitNoNavigation", "swift", "uikit", "Sources/App/SceneDelegate.swift"),
            ("ObjCNoNavigation", "objc", "uikit", "Sources/App/APPSceneDelegate.m"),
        ]
        for name, language, ui, source_path in combinations:
            with self.subTest(language=language, ui=ui), tempfile.TemporaryDirectory() as temp:
                args = self.args(temp, language, ui, "mvvm")
                args.name = name
                args.navigation_enabled = False
                iosflow.generate_project(args)
                source = (Path(temp) / name / source_path).read_text(encoding="utf-8")
                self.assertNotIn("NavigationView", source)
                self.assertNotIn("UINavigationController", source)


if __name__ == "__main__":
    unittest.main()
