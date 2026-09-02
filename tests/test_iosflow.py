import importlib.machinery
import importlib.util
import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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
                self.assertTrue((project / "Checklist.md").exists())
                checklist = (project / "Checklist.md").read_text(encoding="utf-8")
                self.assertIn("## 订阅检查", checklist)
                self.assertIn("## 数据打点检查", checklist)
                self.assertIn("订阅文案与实际价格", checklist)
                self.assertIn("打点位置与事件含义匹配", checklist)
                self.assertTrue((project / "Standards" / "code-style.md").exists())
                self.assertTrue((project / "Resources" / "PrivacyInfo.xcprivacy").exists())
                self.assertTrue((project / "Resources" / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json").exists())
                self.assertTrue((project / "Tests").exists())
                generated_code = [
                    path for directory in (project / "Sources", project / "Tests")
                    for path in directory.rglob("*") if path.suffix in {".swift", ".h", ".m"}
                ]
                for source_file in generated_code:
                    source = source_file.read_text(encoding="utf-8")
                    self.assertNotIn("文件名：", source)
                    self.assertNotIn("创建时间：", source)
                    self.assertNotIn("类型职责：", source)
                    self.assertNotIn("方法职责：", source)
                with (project / "Resources" / "Info.plist").open("rb") as plist_file:
                    info = plistlib.load(plist_file)
                self.assertEqual(info["CFBundleIdentifier"], "$(PRODUCT_BUNDLE_IDENTIFIER)")
                self.assertEqual(info["CFBundleExecutable"], "$(EXECUTABLE_NAME)")
                self.assertEqual(info["CFBundlePackageType"], "$(PRODUCT_BUNDLE_PACKAGE_TYPE)")
                self.assertEqual(info["CFBundleShortVersionString"], "$(MARKETING_VERSION)")
                self.assertEqual(info["CFBundleVersion"], "$(CURRENT_PROJECT_VERSION)")
                self.assertEqual(info["AppDefaultLanguageMode"], "system")
                self.assertEqual(info["AppDefaultLocalization"], "en")
                project_spec = (project / "project.yml").read_text(encoding="utf-8")
                self.assertIn('MARKETING_VERSION: "1.0"', project_spec)
                self.assertIn("ORGANIZATIONNAME: \"Test Team\"", project_spec)
                self.assertNotIn("XCODE_VERSION", project_spec)
                self.assertNotIn(f"  base:\n    PRODUCT_NAME: {project.name}", project_spec)
                self.assertIn(f"      base:\n        PRODUCT_NAME: {project.name}", project_spec)
                self.assertIn("      - path: Resources\n        excludes:\n          - Info.plist", project_spec)

    def test_generated_placeholder_tests_include_todo_and_block_checklist(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.args(temp, "swift", "uikit", "mvvm")
            args.name = "ChecklistApp"
            iosflow.generate_project(args)
            project = Path(temp) / args.name
            test_path = project / "Tests" / "ChecklistAppTests.swift"
            todo_marker = "TO" + "DO:"
            self.assertIn(todo_marker, test_path.read_text(encoding="utf-8"))
            with self.assertRaises(iosflow.WorkflowError):
                iosflow.run_checklist(project, "commit")

            test_path.write_text(
                test_path.read_text(encoding="utf-8").replace(
                    "// " + todo_marker + " 用真实业务场景替换占位测试，并补充成功、失败和边界条件。\n",
                    "",
                ),
                encoding="utf-8",
            )
            iosflow.run_checklist(project, "review")

    def test_interactive_new_uses_numbered_defaults(self):
        defaults = iosflow.load_defaults()
        answers = iter((
            "WizardApp",
            "",  # swift
            "",  # uikit
            "",  # mvvm
            "",  # navigation enabled
            "",  # pod
            "",  # system language
            "",  # comment level 3
            "/tmp",
            "2",  # do not run XcodeGen
        ))
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)), patch.object(
            iosflow, "generate_project"
        ) as generate_project:
            iosflow.interactive_new(defaults)

        args = generate_project.call_args.args[0]
        self.assertEqual(args.name, "WizardApp")
        self.assertEqual(args.language, "swift")
        self.assertEqual(args.ui, "uikit")
        self.assertEqual(args.architecture, "mvvm")
        self.assertTrue(args.navigation_enabled)
        self.assertEqual(args.dependency_manager, "pod")
        self.assertEqual(args.default_language_mode, "system")
        self.assertEqual(args.comment_level, 3)
        self.assertTrue(args.no_xcodegen)

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

    def test_default_language_mode_follows_system(self):
        self.assertEqual(iosflow.load_defaults()["default_language_mode"], "system")

    def test_chinese_comments_default_to_level_three(self):
        defaults = iosflow.load_defaults()
        self.assertEqual(defaults["comment_level"], 3)

    def test_comment_levels_control_explanatory_detail(self):
        cases = (
            (1, (), ("/// 渲染 UIKit 页面", "/// 验证 testExample")),
            (2, ("/// 渲染 UIKit 页面",), ("/// 验证 testExample", "/// 通过系统组件")),
            (3, ("/// 渲染 UIKit 页面", "/// 通过系统组件", "/// 验证 testExample"), ("/// 保存或提供 viewModel",)),
            (4, ("/// 验证 testExample", "/// 保存或提供 viewModel"), ()),
        )
        for level, expected_items, absent_items in cases:
            with self.subTest(level=level), tempfile.TemporaryDirectory() as temp:
                args = self.args(temp, "swift", "uikit", "mvvm")
                args.name = f"CommentApp{level}"
                args.comment_level = level
                iosflow.generate_project(args)
                source_path = Path(temp) / args.name / "Sources" / "Features" / "Home" / "HomeViewController.swift"
                source = source_path.read_text(encoding="utf-8")
                generated_sources = "\n".join(
                    path.read_text(encoding="utf-8")
                    for directory_name in ("Sources", "Tests")
                    for path in (Path(temp) / args.name / directory_name).rglob("*.swift")
                )
                self.assertFalse(source.startswith("//"))
                self.assertNotIn("类型职责：", generated_sources)
                self.assertNotIn("方法职责：", generated_sources)
                for item in expected_items:
                    self.assertIn(item, generated_sources)
                for item in absent_items:
                    self.assertNotIn(item, generated_sources)
                self.assertNotIn("在页面加载后完成基础样式", source)

    def test_system_and_inherited_methods_are_not_annotated(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.args(temp, "swift", "uikit", "mvvm")
            args.name = "SystemMethodComments"
            args.comment_level = 4
            iosflow.generate_project(args)
            project = Path(temp) / args.name
            app_delegate = (project / "Sources" / "App" / "AppDelegate.swift").read_text(encoding="utf-8")
            scene_delegate = (project / "Sources" / "App" / "SceneDelegate.swift").read_text(encoding="utf-8")
            home = (project / "Sources" / "Features" / "Home" / "HomeViewController.swift").read_text(encoding="utf-8")
            self.assertNotIn("响应应用创建新 scene", app_delegate)
            self.assertNotIn("在 scene 连接时创建窗口", scene_delegate)
            self.assertNotIn("在页面加载后完成基础样式", home)
            self.assertNotIn("保存或提供 label", home)
            tests = (project / "Tests" / f"{args.name}Tests.swift").read_text(encoding="utf-8")
            self.assertIn("/// 验证 testExample", tests)

    def test_existing_file_metadata_header_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_path = base / "Sources" / "Preserved.swift"
            source_path.parent.mkdir(parents=True)
            original_header = "\n".join((
                "//",
                "//  Preserved.swift",
                "//  ExistingProject",
                "//",
                "//  Created by Xcode on an existing date.",
                "//",
            ))
            source_path.write_text(
                original_header + "\n\nimport Foundation\n\nfunc performBusinessWork() {}\n",
                encoding="utf-8",
            )
            options = iosflow.load_defaults()
            iosflow.add_chinese_comments(base, "DifferentProject", options)
            iosflow.add_chinese_comments(base, "DifferentProject", options)
            result = source_path.read_text(encoding="utf-8")
            self.assertTrue(result.startswith("import Foundation"))
            self.assertNotIn("Preserved.swift", result)
            self.assertNotIn("Created by Xcode", result)
            self.assertIn("/// 执行 performBusinessWork", result)

    def test_rejects_unsupported_comment_level(self):
        options = iosflow.load_defaults()
        options["comment_level"] = 5
        with self.assertRaises(iosflow.WorkflowError):
            iosflow.validate_options(options)

    def test_rejects_unsupported_default_language_mode(self):
        options = iosflow.load_defaults()
        options["default_language_mode"] = "automatic"
        with self.assertRaises(iosflow.WorkflowError):
            iosflow.validate_options(options)

    def test_fixed_language_mode_override_is_written_to_project_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.args(temp, "swift", "uikit", "mvvm")
            args.name = "SystemLanguageApp"
            args.default_language_mode = "fixed"
            iosflow.generate_project(args)
            project = Path(temp) / "SystemLanguageApp"
            with (project / "Resources" / "Info.plist").open("rb") as plist_file:
                info = plistlib.load(plist_file)
            workflow = iosflow.json.loads((project / "workflow.json").read_text(encoding="utf-8"))
            self.assertEqual(info["AppDefaultLanguageMode"], "fixed")
            self.assertEqual(workflow["default_language_mode"], "fixed")

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
