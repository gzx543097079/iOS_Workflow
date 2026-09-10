"""校验工作流配置并生成可复现的最小 iOS 项目骨架。"""

from __future__ import annotations

import json
from copy import deepcopy
import math
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Iterable, List, Tuple


# schema_version=1 的固定字段契约，不依赖可更新的共享默认文件。
INSTANCE_CONFIG_KEYS = frozenset({
    "architecture",
    "build_number",
    "bundle_id",
    "bundle_id_prefix",
    "code_sign_style",
    "comment_level",
    "default_language_mode",
    "default_localization",
    "dependency_manager",
    "deployment_target",
    "development_team",
    "generate_privacy_manifest",
    "generate_xcodeproj",
    "include_ui_tests",
    "include_unit_tests",
    "language",
    "localization_strings",
    "marketing_version",
    "navigation_enabled",
    "objc_class_prefix",
    "organization_name",
    "strict_concurrency",
    "supported_localizations",
    "supported_orientations",
    "supports_dark_mode",
    "supports_manual_dark_mode_switch",
    "swift_version",
    "target_devices",
    "test_framework",
    "ui",
    "warnings_as_errors",
})

# 当前源码模板的能力下限，不是项目默认值；UIKit 使用 Scene 生命周期，SwiftUI 使用 App 生命周期。
GENERATION_MINIMUM_IOS = {
    ("swift", "uikit"): "13.0",
    ("objc", "uikit"): "13.0",
    ("swift", "swiftui"): "14.0",
}


class ConfigurationError(ValueError):
    """配置无法安全生成项目时抛出的错误。"""


def strip_jsonc(text: str) -> str:
    """移除 JSONC 注释，同时保留字符串中的注释符号。"""
    output: List[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
        elif char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
        elif char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                index += 1
            if index + 1 >= len(text):
                raise ConfigurationError("JSONC 包含未闭合的块注释")
            index += 2
        else:
            output.append(char)
            index += 1
    return "".join(output)


def load_jsonc(path: Path) -> Dict[str, Any]:
    """读取 JSONC 对象并提供清晰的格式错误。"""
    try:
        value = json.loads(strip_jsonc(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigurationError(f"无法读取配置 {path}: {error}") from error
    if not isinstance(value, dict):
        raise ConfigurationError(f"配置根节点必须是对象: {path}")
    return value


def _diagnose_keys(value: Dict[str, Any], required: Iterable[str], path: str,
                   *, optional: Iterable[str] = ()) -> List[str]:
    required, optional = set(required), set(optional)
    prefix = f"{path}." if path else ""
    errors = [f"{prefix}{key} 缺失" for key in sorted(required - set(value))]
    errors.extend(f"{prefix}{key} 未知字段" for key in sorted(set(value) - required - optional, key=str))
    return errors


def diagnose_project_instance(instance: Any) -> List[str]:
    """一次汇总首次生成输入的问题，不补值、不修改输入、不读取或写入文件。"""
    if not isinstance(instance, dict):
        return ["instance 必须是对象"]
    required = {"schema_version", "project_name", "config", "design_tokens", "sources", "constraints"}
    errors = _diagnose_keys(instance, required, "")
    if "schema_version" in instance and (type(instance["schema_version"]) is not int or instance["schema_version"] != 1):
        errors.append("schema_version 不受支持；可选值：整数 1，需要显式迁移")
    if "project_name" in instance:
        name = instance["project_name"]
        if not isinstance(name, str) or not name.strip():
            errors.append("project_name 必须是非空字符串")
        elif not re.search(r"[A-Za-z0-9]", name):
            errors.append("project_name 必须包含英文字母或数字，以生成工程名称")
    if "config" in instance:
        errors.extend(_diagnose_config(instance["config"]))
    if "design_tokens" in instance:
        errors.extend(_diagnose_design_tokens(instance["design_tokens"]))
    if "sources" in instance:
        sources = instance["sources"]
        if not isinstance(sources, dict):
            errors.append("sources 必须是为每个配置字段记录来源的对象")
        else:
            errors.extend(_diagnose_keys(sources, INSTANCE_CONFIG_KEYS, "sources"))
            for key, value in sources.items():
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"sources.{key} 必须是非空来源说明")
    if "constraints" in instance:
        constraints = instance["constraints"]
        if not isinstance(constraints, list):
            errors.append("constraints 必须是非空字符串组成的数组")
        else:
            for index, value in enumerate(constraints):
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"constraints[{index}] 必须是非空字符串")
    return errors


def validate_project_instance(instance: Dict[str, Any]) -> Dict[str, Any]:
    """仅校验首次生成输入，并一次报告全部诊断，不补全字段或加载示例。"""
    errors = diagnose_project_instance(instance)
    if errors:
        raise ConfigurationError("项目配置校验失败：\n" + "\n".join(f"- {error}" for error in errors))
    return deepcopy(instance)


def load_project_instance(path: Path) -> Dict[str, Any]:
    """读取首次生成项目使用的配置实例。"""
    return validate_project_instance(load_jsonc(path))


def save_project_instance(path: Path, instance: Dict[str, Any]) -> None:
    """保存新实例，不覆盖已存在的配置；更新由客户端显式展示 diff 后处理。"""
    value = validate_project_instance(instance)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _diagnose_config(config: Any) -> List[str]:
    if not isinstance(config, dict):
        return ["config 必须是对象"]
    errors = _diagnose_keys(config, INSTANCE_CONFIG_KEYS, "config")
    choices = {
        "language": ("swift", "objc"), "ui": ("uikit", "swiftui"),
        "architecture": ("mvvm", "mvc"), "dependency_manager": ("pod", "spm", "carthage", "none"),
        "default_language_mode": ("system", "fixed"), "test_framework": ("xctest",),
        "strict_concurrency": ("minimal", "targeted", "complete"), "code_sign_style": ("automatic", "manual"),
        "swift_version": ("5", "6"),
    }
    for key, allowed in choices.items():
        if key in config and (not isinstance(config[key], str) or config[key] not in allowed):
            errors.append(f"config.{key} 无效；可选值：{', '.join(allowed)}")
    if config.get("language") == "objc" and config.get("ui") == "swiftui":
        errors.append("config.language / config.ui：Objective-C 项目不支持 SwiftUI，请选择 UIKit 或 Swift")
    patterns = {
        "deployment_target": (r"[0-9]+\.[0-9]+", "major.minor 字符串"),
        "marketing_version": (r"[0-9]+(?:\.[0-9]+){1,2}", "数字版本字符串"),
        "build_number": (r"[0-9]+", "正整数字符串"),
        "objc_class_prefix": (r"[A-Z]{2,3}", "2–3 个大写字母"),
        "bundle_id_prefix": (r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", "反向域名字符串"),
        "bundle_id": (r"(?:[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)?", "空字符串或反向域名字符串"),
    }
    for key, (pattern, description) in patterns.items():
        if key in config and (not isinstance(config[key], str) or not re.fullmatch(pattern, config[key])):
            errors.append(f"config.{key} 必须是{description}")
    language, ui, deployment = config.get("language"), config.get("ui"), config.get("deployment_target")
    if isinstance(language, str) and isinstance(ui, str) and isinstance(deployment, str) and re.fullmatch(r"[0-9]+\.[0-9]+", deployment):
        minimum = GENERATION_MINIMUM_IOS.get((language, ui))
        if minimum and tuple(map(int, deployment.split("."))) < tuple(map(int, minimum.split("."))):
            errors.append(f"config.deployment_target：当前 {language}/{ui} 骨架最低支持 iOS {minimum}，不支持 {deployment}；保留需求，改用兼容的工程实现或扩展模板，不自动提高部署版本")
    if isinstance(config.get("build_number"), str) and re.fullmatch(r"0+", config["build_number"]):
        errors.append("config.build_number 必须是大于 0 的正整数字符串")
    if "comment_level" in config and (type(config["comment_level"]) is not int or config["comment_level"] not in (1, 2, 3, 4)):
        errors.append("config.comment_level 必须是整数；可选值：1, 2, 3, 4")
    for key in ("organization_name", "development_team", "default_localization"):
        if key in config and not isinstance(config[key], str):
            errors.append(f"config.{key} 必须是字符串")
    localizations = config.get("supported_localizations")
    valid_localizations = isinstance(localizations, list) and bool(localizations) and all(isinstance(x, str) and x.strip() for x in localizations)
    if "supported_localizations" in config and not valid_localizations:
        errors.append("config.supported_localizations 必须是非空字符串数组")
    if valid_localizations:
        seen_localizations = set()
        for index, locale in enumerate(localizations):
            # Accept portable hyphenated language tags, never filesystem paths.
            if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", locale):
                errors.append(f"config.supported_localizations[{index}] 必须是使用连字符的语言标识，不允许路径或特殊字符")
            if locale.casefold() in seen_localizations:
                errors.append(f"config.supported_localizations[{index}] 语言标识重复（不区分大小写）")
            seen_localizations.add(locale.casefold())
    if valid_localizations and "default_localization" in config and config["default_localization"] not in localizations:
        errors.append("config.default_localization 必须包含在 config.supported_localizations 中")
    localization_strings = config.get("localization_strings")
    if "localization_strings" in config and (not isinstance(localization_strings, dict) or not localization_strings):
        errors.append("config.localization_strings 必须是非空对象")
    if isinstance(localization_strings, dict):
        for key, translations in localization_strings.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(translations, dict):
                errors.append(f"config.localization_strings.{key} 必须使用非空字符串键和语言映射")
                continue
            if valid_localizations:
                missing = [locale for locale in localizations if not isinstance(translations.get(locale), str) or not translations[locale]]
                if missing:
                    errors.append(f"config.localization_strings.{key} 缺少语言: {', '.join(missing)}")
    for key, allowed, allow_empty in (
        ("target_devices", ("iphone", "ipad"), False),
        ("supported_orientations", ("portrait", "portrait_upside_down", "landscape_left", "landscape_right"), True),
    ):
        if key not in config:
            continue
        value = config[key]
        if (not isinstance(value, list) or (not allow_empty and not value)
                or not all(isinstance(x, str) and x in allowed for x in value)):
            errors.append(f"config.{key} 必须是{'可为空的' if allow_empty else '非空'}数组；可选值：{', '.join(allowed)}")
        elif len(set(value)) != len(value):
            errors.append(f"config.{key} 包含重复值；可选值：{', '.join(allowed)}")
    boolean_keys = (
        "navigation_enabled",
        "supports_dark_mode",
        "supports_manual_dark_mode_switch",
        "include_unit_tests",
        "include_ui_tests",
        "warnings_as_errors",
        "generate_privacy_manifest",
        "generate_xcodeproj",
    )
    for key in boolean_keys:
        if key in config and not isinstance(config[key], bool):
            errors.append(f"config.{key} 必须是布尔值；可选值：true, false")
    if config.get("supports_manual_dark_mode_switch") is True and config.get("supports_dark_mode") is False:
        errors.append("config.supports_manual_dark_mode_switch 只能在 supports_dark_mode 为 true 时开启")
    return errors


def _diagnose_design_tokens(tokens: Any) -> List[str]:
    if not isinstance(tokens, dict):
        return ["design_tokens 必须是对象"]
    maps = ("spacing", "radius", "control_height", "icon_size", "border_width", "opacity", "animation_duration")
    scalars = ("content_margin", "content_max_width", "minimum_tap_target")
    errors = _diagnose_keys(tokens, (*maps, *scalars, "typography", "colors"), "design_tokens", optional=("version",))
    def is_number(value: Any) -> bool:
        return type(value) is int or (type(value) is float and math.isfinite(value))
    if "version" in tokens and (type(tokens["version"]) is not int or tokens["version"] < 1):
        errors.append("design_tokens.version 必须是正整数")
    for key in maps:
        if key not in tokens:
            continue
        value = tokens[key]
        if not isinstance(value, dict) or not value:
            errors.append(f"design_tokens.{key} 必须是非空对象")
            continue
        for name, number in value.items():
            if not isinstance(name, str) or not name.strip():
                errors.append(f"design_tokens.{key}.{name} 必须使用非空字符串键")
            if not is_number(number):
                errors.append(f"design_tokens.{key}.{name} 必须是有限数字，不能是布尔值")
    for key in scalars:
        if key in tokens and not is_number(tokens[key]):
            errors.append(f"design_tokens.{key} 必须是有限数字，不能是布尔值")
    supported_text_styles = ("largeTitle", "title", "title2", "title3", "headline", "subheadline", "body", "callout", "footnote", "caption", "caption2")
    for key in ("typography", "colors"):
        if key not in tokens:
            continue
        value = tokens[key]
        if not isinstance(value, dict) or not value:
            errors.append(f"design_tokens.{key} 必须是非空字符串对象")
            continue
        for name, text in value.items():
            if not isinstance(name, str) or not name.strip() or not isinstance(text, str) or not text.strip():
                errors.append(f"design_tokens.{key}.{name} 必须使用非空字符串键和值")
            elif key == "typography" and text not in supported_text_styles:
                errors.append(f"design_tokens.typography.{name} 不支持此系统文字样式；可选值：{', '.join(supported_text_styles)}")
    return errors


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """保持独立配置校验 API，并汇总报告全部字段和组合问题。"""
    errors = _diagnose_config(config)
    if errors:
        raise ConfigurationError("\n".join(errors))
    return dict(config)


def validate_design_tokens(tokens: Dict[str, Any]) -> Dict[str, Any]:
    """验证生成代码需要的 DesignTokens 字段和数值。"""
    errors = _diagnose_design_tokens(tokens)
    if errors:
        raise ConfigurationError("\n".join(errors))
    return dict(tokens)


def _swift_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    if not parts:
        raise ConfigurationError("项目名必须包含字母或数字")
    name = "".join(part[:1].upper() + part[1:] for part in parts)
    return f"App{name}" if name[0].isdigit() else name


def _camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _number(value: Any) -> str:
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def _uikit_text_style(value: str) -> str:
    return "caption1" if value == "caption" else value


def render_swift_design_tokens(tokens: Dict[str, Any], ui: str, comment_level: int = 1) -> str:
    """生成 Swift UIKit 或 SwiftUI DesignTokens。"""
    validate_design_tokens(tokens)
    imports = "import SwiftUI\nimport UIKit" if ui == "swiftui" else "import UIKit"
    lines = [imports, ""]
    if comment_level >= 2:
        lines.append("// 集中定义界面使用的尺寸、颜色和动效常量，避免业务页面散落魔法数字。")
    lines.append("enum DesignTokens {")
    groups: List[Tuple[str, str, Dict[str, Any]]] = [
        ("Spacing", "CGFloat", tokens["spacing"]),
        ("Radius", "CGFloat", tokens["radius"]),
        ("ControlHeight", "CGFloat", tokens["control_height"]),
        ("IconSize", "CGFloat", tokens["icon_size"]),
        ("BorderWidth", "CGFloat", tokens["border_width"]),
        ("Opacity", "Double", tokens["opacity"]),
        ("AnimationDuration", "TimeInterval", tokens["animation_duration"]),
    ]
    for title, value_type, values in groups:
        if comment_level >= 3:
            lines.append(f"    // {title} 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。")
        lines.append(f"    enum {title} {{")
        for key, value in values.items():
            lines.append(f"        static let {_camel(key)}: {value_type} = {_number(value)}")
        lines.append("    }")
        lines.append("")
    for key, value in (("contentMargin", tokens["content_margin"]), ("contentMaxWidth", tokens["content_max_width"]), ("minimumTapTarget", tokens["minimum_tap_target"])):
        lines.append(f"    static let {key}: CGFloat = {_number(value)}")
    lines.append("")
    typography_type = "Font" if ui == "swiftui" else "UIFont.TextStyle"
    lines.append("    enum Typography {")
    for key, value in tokens["typography"].items():
        expression = f"Font.{value}" if ui == "swiftui" else f"UIFont.TextStyle.{_uikit_text_style(value)}"
        lines.append(f"        static let {_camel(key)}: {typography_type} = {expression}")
    lines.extend(["    }", ""])
    color_type = "Color" if ui == "swiftui" else "UIColor"
    lines.append("    enum Colors {")
    for key, value in tokens["colors"].items():
        expression = f"Color(UIColor.{value})" if ui == "swiftui" else f"UIColor.{value}"
        lines.append(f"        static let {_camel(key)}: {color_type} = {expression}")
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def render_objc_design_tokens(tokens: Dict[str, Any], comment_level: int = 1) -> Tuple[str, str]:
    """生成 Objective-C DesignTokens 头文件与实现。"""
    validate_design_tokens(tokens)
    header = ["#import <UIKit/UIKit.h>", "", "NS_ASSUME_NONNULL_BEGIN", ""]
    if comment_level >= 2:
        header.append("// 集中定义界面使用的尺寸和颜色常量，避免业务页面散落魔法数字。")
    header.append("@interface DesignTokens : NSObject")
    implementation = ["#import \"DesignTokens.h\"", "", "@implementation DesignTokens"]
    numeric_groups = (
        ("spacing", "CGFloat", tokens["spacing"]),
        ("radius", "CGFloat", tokens["radius"]),
        ("controlHeight", "CGFloat", tokens["control_height"]),
        ("iconSize", "CGFloat", tokens["icon_size"]),
        ("borderWidth", "CGFloat", tokens["border_width"]),
        ("opacity", "CGFloat", tokens["opacity"]),
        ("animationDuration", "NSTimeInterval", tokens["animation_duration"]),
    )
    for group, return_type, values in numeric_groups:
        for key, value in values.items():
            method = group + key[:1].upper() + _camel(key)[1:]
            header.append(f"+ ({return_type}){method};")
            implementation.extend([f"+ ({return_type}){method} {{", f"    return {_number(value)};", "}"])
    scalar_values = (("contentMargin", tokens["content_margin"]), ("contentMaxWidth", tokens["content_max_width"]), ("minimumTapTarget", tokens["minimum_tap_target"]))
    for method, value in scalar_values:
        header.append(f"+ (CGFloat){method};")
        implementation.extend([f"+ (CGFloat){method} {{", f"    return {_number(value)};", "}"])
    for key, value in tokens["typography"].items():
        method = "typography" + key[:1].upper() + _camel(key)[1:]
        style = _uikit_text_style(value)
        constant = "UIFontTextStyle" + style[:1].upper() + style[1:]
        header.append(f"+ (UIFontTextStyle){method};")
        implementation.extend([f"+ (UIFontTextStyle){method} {{", f"    return {constant};", "}"])
    for key, value in tokens["colors"].items():
        method = "color" + key[:1].upper() + _camel(key)[1:]
        header.append(f"+ (UIColor *){method};")
        implementation.extend([f"+ (UIColor *){method} {{", f"    return UIColor.{value}Color;", "}"])
    header.extend(["@end", "", "NS_ASSUME_NONNULL_END", ""])
    implementation.extend(["@end", ""])
    return "\n".join(header), "\n".join(implementation)


def _comment(level: int, text: str, indent: str = "") -> str:
    return f"{indent}// {text}\n" if level >= 2 else ""


def _swift_localization_policy(level: int) -> str:
    method_comment = _comment(level, "根据项目语言策略解析文案；固定语言资源不可用时回退到系统语言。", "    ") if level >= 3 else ""
    return f'''import Foundation

enum LocalizationPolicy {{
    private static let mode = "__LANGUAGE_MODE__"
    private static let defaultLocalization = "__DEFAULT_LOCALIZATION__"

{method_comment}    static func localized(_ key: String) -> String {{
        guard mode == "fixed",
              let path = Bundle.main.path(forResource: defaultLocalization, ofType: "lproj"),
              let bundle = Bundle(path: path) else {{
            return NSLocalizedString(key, comment: "")
        }}
        return bundle.localizedString(forKey: key, value: nil, table: nil)
    }}
}}
'''


def _swift_view_model(level: int) -> str:
    comment = _comment(level, "首页 Model 保存展示所需的本地化键，避免视图直接持有业务文案。")
    return f'''import Foundation

{comment}struct HomeViewModel {{
    let titleKey = "home.title"
}}
'''


def _swift_uikit_appearance_policy(level: int) -> str:
    comment = _comment(level, "保存用户选择的外观模式，并把跟随系统、浅色或深色应用到当前窗口。")
    return f'''import UIKit

{comment}enum AppearancePolicy {{
    enum Mode: String {{
        case system
        case light
        case dark

        var interfaceStyle: UIUserInterfaceStyle {{
            switch self {{
            case .system: return .unspecified
            case .light: return .light
            case .dark: return .dark
            }}
        }}
    }}

    static let storageKey = "app.appearance"

    @MainActor
    static func apply(to window: UIWindow) {{
        let value = UserDefaults.standard.string(forKey: storageKey)
        window.overrideUserInterfaceStyle = Mode(rawValue: value ?? "")?.interfaceStyle ?? .unspecified
    }}

    @MainActor
    static func set(_ mode: Mode, for window: UIWindow) {{
        UserDefaults.standard.set(mode.rawValue, forKey: storageKey)
        window.overrideUserInterfaceStyle = mode.interfaceStyle
    }}
}}
'''


def _swiftui_appearance_policy(level: int) -> str:
    comment = _comment(level, "定义可持久化的外观选项；设置页面可使用相同 storageKey 写入用户选择。")
    return f'''import SwiftUI

{comment}enum AppAppearance: String {{
    case system
    case light
    case dark

    var colorScheme: ColorScheme? {{
        switch self {{
        case .system: return nil
        case .light: return .light
        case .dark: return .dark
        }}
    }}
}}

enum AppearancePolicy {{
    static let storageKey = "app.appearance"
}}
'''


def _swift_uikit_sources(name: str, level: int, architecture: str, navigation_enabled: bool, manual_appearance: bool) -> Dict[str, str]:
    page_comment = _comment(level, "首页展示应用的基础内容，并作为后续业务模块的入口。")
    method_comment = _comment(level, "集中创建视图层级和约束，避免初始化流程散落在生命周期方法中。", "    ") if level >= 3 else ""
    root = "UINavigationController(rootViewController: HomeViewController())" if navigation_enabled else "HomeViewController()"
    view_model_property = "    private let viewModel = HomeViewModel()\n" if architecture == "mvvm" else ""
    title_key = "viewModel.titleKey" if architecture == "mvvm" else '"home.title"'
    appearance_apply = "        AppearancePolicy.apply(to: window)\n" if manual_appearance else ""
    sources = {
        "App/AppDelegate.swift": "import UIKit\n\n@main\nfinal class AppDelegate: UIResponder, UIApplicationDelegate {\n    func application(_ application: UIApplication, configurationForConnecting connectingSceneSession: UISceneSession, options: UIScene.ConnectionOptions) -> UISceneConfiguration {\n        UISceneConfiguration(name: \"Default Configuration\", sessionRole: connectingSceneSession.role)\n    }\n}\n",
        "App/SceneDelegate.swift": f"import UIKit\n\nfinal class SceneDelegate: UIResponder, UIWindowSceneDelegate {{\n    var window: UIWindow?\n\n    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {{\n        guard let windowScene = scene as? UIWindowScene else {{ return }}\n        let window = UIWindow(windowScene: windowScene)\n        window.rootViewController = {root}\n{appearance_apply}        window.makeKeyAndVisible()\n        self.window = window\n    }}\n}}\n",
        "App/Features/Home/HomeViewController.swift": f"import UIKit\n\n{page_comment}final class HomeViewController: UIViewController {{\n{view_model_property}    private let titleLabel = UILabel()\n\n    override func viewDidLoad() {{\n        super.viewDidLoad()\n        configureHierarchy()\n    }}\n\n{method_comment}    private func configureHierarchy() {{\n        view.backgroundColor = DesignTokens.Colors.background\n        titleLabel.text = LocalizationPolicy.localized({title_key})\n        titleLabel.font = .preferredFont(forTextStyle: .title2)\n        titleLabel.translatesAutoresizingMaskIntoConstraints = false\n        view.addSubview(titleLabel)\n        NSLayoutConstraint.activate([\n            titleLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),\n            titleLabel.centerYAnchor.constraint(equalTo: view.centerYAnchor)\n        ])\n    }}\n}}\n",
    }
    if architecture == "mvvm":
        sources["App/Features/Home/HomeViewModel.swift"] = _swift_view_model(level)
    if manual_appearance:
        sources["App/Core/Appearance/AppearancePolicy.swift"] = _swift_uikit_appearance_policy(level)
    return sources


def _swiftui_sources(name: str, level: int, architecture: str, navigation_enabled: bool, manual_appearance: bool) -> Dict[str, str]:
    comment = _comment(level, "首页展示应用的基础内容，并作为后续业务模块的入口。")
    view_model_property = "    private let viewModel = HomeViewModel()\n" if architecture == "mvvm" else ""
    title_key = "viewModel.titleKey" if architecture == "mvvm" else '"home.title"'
    content = f'''Text(LocalizationPolicy.localized({title_key}))
            .font(.title2)
            .foregroundColor(DesignTokens.Colors.primaryText)'''
    if navigation_enabled:
        content = f'''NavigationView {{
            {content}
                .navigationTitle(LocalizationPolicy.localized({title_key}))
        }}'''
    appearance_state = "    @AppStorage(AppearancePolicy.storageKey) private var appearance = AppAppearance.system.rawValue\n\n" if manual_appearance else ""
    appearance_modifier = "\n                .preferredColorScheme(AppAppearance(rawValue: appearance)?.colorScheme)" if manual_appearance else ""
    sources = {
        f"App/{name}App.swift": f"import SwiftUI\n\n@main\nstruct {name}App: App {{\n{appearance_state}    var body: some Scene {{\n        WindowGroup {{\n            HomeView(){appearance_modifier}\n        }}\n    }}\n}}\n",
        "App/Features/Home/HomeView.swift": f"import SwiftUI\n\n{comment}struct HomeView: View {{\n{view_model_property}    var body: some View {{\n        {content}\n    }}\n}}\n",
    }
    if architecture == "mvvm":
        sources["App/Features/Home/HomeViewModel.swift"] = _swift_view_model(level)
    if manual_appearance:
        sources["App/Core/Appearance/AppearancePolicy.swift"] = _swiftui_appearance_policy(level)
    return sources


def _objc_appearance_policy(prefix: str, level: int) -> Dict[str, str]:
    name = f"{prefix}AppearancePolicy"
    comment = "// 保存用户选择的外观模式，并把跟随系统、浅色或深色应用到当前窗口。\n" if level >= 2 else ""
    return {
        f"App/Core/Appearance/{name}.h": f'''#import <UIKit/UIKit.h>

typedef NS_ENUM(NSInteger, {prefix}AppearanceMode) {{
    {prefix}AppearanceModeSystem,
    {prefix}AppearanceModeLight,
    {prefix}AppearanceModeDark,
}};

{comment}@interface {name} : NSObject
+ (void)applyToWindow:(UIWindow *)window;
+ (void)setMode:({prefix}AppearanceMode)mode forWindow:(UIWindow *)window;
@end
''',
        f"App/Core/Appearance/{name}.m": f'''#import "{name}.h"

static NSString * const {prefix}AppearanceStorageKey = @"app.appearance";

@implementation {name}
+ (UIUserInterfaceStyle)interfaceStyleForMode:({prefix}AppearanceMode)mode {{
    switch (mode) {{
        case {prefix}AppearanceModeLight: return UIUserInterfaceStyleLight;
        case {prefix}AppearanceModeDark: return UIUserInterfaceStyleDark;
        default: return UIUserInterfaceStyleUnspecified;
    }}
}}

+ (void)applyToWindow:(UIWindow *)window {{
    NSInteger mode = [NSUserDefaults.standardUserDefaults integerForKey:{prefix}AppearanceStorageKey];
    window.overrideUserInterfaceStyle = [self interfaceStyleForMode:mode];
}}

+ (void)setMode:({prefix}AppearanceMode)mode forWindow:(UIWindow *)window {{
    [NSUserDefaults.standardUserDefaults setInteger:mode forKey:{prefix}AppearanceStorageKey];
    window.overrideUserInterfaceStyle = [self interfaceStyleForMode:mode];
}}
@end
''',
    }


def _objc_sources(prefix: str, level: int, architecture: str, navigation_enabled: bool, manual_appearance: bool) -> Dict[str, str]:
    page_comment = "// 首页展示应用的基础内容，并作为后续业务模块的入口。\n" if level >= 2 else ""
    method_comment = "// 集中创建视图层级和约束，避免初始化流程散落在生命周期方法中。\n" if level >= 3 else ""
    app_delegate = f"{prefix}AppDelegate"
    scene_delegate = f"{prefix}SceneDelegate"
    home = f"{prefix}HomeViewController"
    root = f"[[UINavigationController alloc] initWithRootViewController:[{home} new]]" if navigation_enabled else f"[{home} new]"
    model_header = f'#import "{prefix}HomeViewModel.h"\n' if architecture == "mvvm" else ""
    model_property = f"@property (nonatomic, strong) {prefix}HomeViewModel *viewModel;\n" if architecture == "mvvm" else ""
    model_setup = f"    self.viewModel = [{prefix}HomeViewModel new];\n" if architecture == "mvvm" else ""
    title_key = "self.viewModel.titleKey" if architecture == "mvvm" else '@"home.title"'
    appearance_import = f'#import "{prefix}AppearancePolicy.h"\n' if manual_appearance else ""
    appearance_apply = f"    [{prefix}AppearancePolicy applyToWindow:self.window];\n" if manual_appearance else ""
    sources = {
        "App/main.m": f"#import <UIKit/UIKit.h>\n#import \"{app_delegate}.h\"\n\nint main(int argc, char * argv[]) {{\n    @autoreleasepool {{\n        return UIApplicationMain(argc, argv, nil, NSStringFromClass({app_delegate}.class));\n    }}\n}}\n",
        f"App/{app_delegate}.h": f"#import <UIKit/UIKit.h>\n\n@interface {app_delegate} : UIResponder <UIApplicationDelegate>\n@end\n",
        f"App/{app_delegate}.m": f"#import \"{app_delegate}.h\"\n\n@implementation {app_delegate}\n- (UISceneConfiguration *)application:(UIApplication *)application configurationForConnectingSceneSession:(UISceneSession *)connectingSceneSession options:(UISceneConnectionOptions *)options {{\n    return [[UISceneConfiguration alloc] initWithName:@\"Default Configuration\" sessionRole:connectingSceneSession.role];\n}}\n@end\n",
        f"App/{scene_delegate}.h": f"#import <UIKit/UIKit.h>\n\n@interface {scene_delegate} : UIResponder <UIWindowSceneDelegate>\n@property (nonatomic, strong) UIWindow *window;\n@end\n",
        f"App/{scene_delegate}.m": f"#import \"{scene_delegate}.h\"\n#import \"{home}.h\"\n{appearance_import}\n@implementation {scene_delegate}\n- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)connectionOptions {{\n    if (![scene isKindOfClass:UIWindowScene.class]) {{ return; }}\n    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];\n    self.window.rootViewController = {root};\n{appearance_apply}    [self.window makeKeyAndVisible];\n}}\n@end\n",
        f"App/Features/Home/{home}.h": f"#import <UIKit/UIKit.h>\n\n{page_comment}@interface {home} : UIViewController\n@end\n",
        f"App/Features/Home/{home}.m": f"#import \"{home}.h\"\n#import \"DesignTokens.h\"\n#import \"{prefix}LocalizationPolicy.h\"\n{model_header}\n@interface {home} ()\n{model_property}@property (nonatomic, strong) UILabel *titleLabel;\n@end\n\n@implementation {home}\n- (void)viewDidLoad {{\n    [super viewDidLoad];\n{model_setup}    [self configureHierarchy];\n}}\n\n{method_comment}- (void)configureHierarchy {{\n    self.view.backgroundColor = [DesignTokens colorBackground];\n    self.titleLabel = [UILabel new];\n    self.titleLabel.text = [{prefix}LocalizationPolicy localizedStringForKey:{title_key}];\n    self.titleLabel.translatesAutoresizingMaskIntoConstraints = NO;\n    [self.view addSubview:self.titleLabel];\n    [NSLayoutConstraint activateConstraints:@[[self.titleLabel.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor], [self.titleLabel.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor]]];\n}}\n@end\n",
    }
    if architecture == "mvvm":
        model_comment = page_comment.replace("首页展示应用的基础内容，并作为后续业务模块的入口。", "首页 Model 保存展示所需的本地化键，避免视图直接持有业务文案。")
        sources[f"App/Features/Home/{prefix}HomeViewModel.h"] = f"#import <Foundation/Foundation.h>\n\n{model_comment}@interface {prefix}HomeViewModel : NSObject\n@property (nonatomic, copy, readonly) NSString *titleKey;\n@end\n"
        sources[f"App/Features/Home/{prefix}HomeViewModel.m"] = f"#import \"{prefix}HomeViewModel.h\"\n\n@implementation {prefix}HomeViewModel\n- (NSString *)titleKey {{ return @\"home.title\"; }}\n@end\n"
    if manual_appearance:
        sources.update(_objc_appearance_policy(prefix, level))
    return sources


def _objc_localization_policy(prefix: str, level: int) -> Dict[str, str]:
    method_comment = "// 根据项目语言策略解析文案；固定语言资源不可用时回退到系统语言。\n" if level >= 3 else ""
    name = f"{prefix}LocalizationPolicy"
    return {
        f"App/Core/Localization/{name}.h": f'''#import <Foundation/Foundation.h>

@interface {name} : NSObject
+ (NSString *)localizedStringForKey:(NSString *)key;
@end
''',
        f"App/Core/Localization/{name}.m": f'''#import "{name}.h"

@implementation {name}
{method_comment}+ (NSString *)localizedStringForKey:(NSString *)key {{
    NSString *mode = @"__LANGUAGE_MODE__";
    if (![mode isEqualToString:@"fixed"]) {{
        return NSLocalizedString(key, nil);
    }}
    NSString *path = [NSBundle.mainBundle pathForResource:@"__DEFAULT_LOCALIZATION__" ofType:@"lproj"];
    NSBundle *bundle = path == nil ? nil : [NSBundle bundleWithPath:path];
    return bundle == nil ? NSLocalizedString(key, nil) : [bundle localizedStringForKey:key value:nil table:nil];
}}
@end
''',
    }


def _project_yml(name: str, config: Dict[str, Any]) -> str:
    bundle_id = config.get("bundle_id") or f"{config['bundle_id_prefix']}.{name.lower()}"
    test_lines = ""
    if config["include_unit_tests"]:
        test_lines += f"  {name}Tests:\n    type: bundle.unit-test\n    platform: iOS\n    sources: [Tests]\n    dependencies:\n      - target: {name}\n"
    if config["include_ui_tests"]:
        test_lines += f"  {name}UITests:\n    type: bundle.ui-testing\n    platform: iOS\n    sources: [UITests]\n    dependencies:\n      - target: {name}\n"
    swift_setting = ""
    if config["language"] == "swift":
        swift_setting = f'        SWIFT_VERSION: "{config["swift_version"]}"\n        SWIFT_STRICT_CONCURRENCY: {config["strict_concurrency"]}\n'
    warnings = "YES" if config["warnings_as_errors"] else "NO"
    device_family = ",".join("1" if item == "iphone" else "2" for item in config["target_devices"])
    team_setting = f"        DEVELOPMENT_TEAM: {config['development_team']}\n" if config["development_team"] else ""
    generated_info_setting = ""
    if config["ui"] == "swiftui":
        generated_info_setting = "        GENERATE_INFOPLIST_FILE: YES\n        INFOPLIST_KEY_UILaunchScreen_Generation: YES\n"
        if not config["supports_dark_mode"]:
            generated_info_setting += "        INFOPLIST_KEY_UIUserInterfaceStyle: Light\n"
    info_section = ""
    if config["ui"] == "uikit":
        scene_delegate = "$(PRODUCT_MODULE_NAME).SceneDelegate" if config["language"] == "swift" else f"{config['objc_class_prefix']}SceneDelegate"
        appearance_property = "        UIUserInterfaceStyle: Light\n" if not config["supports_dark_mode"] else ""
        info_section = f'''    info:
      path: App/Resources/Info.plist
      properties:
        UILaunchScreen: {{}}
{appearance_property}        UIApplicationSceneManifest:
          UIApplicationSupportsMultipleScenes: false
          UISceneConfigurations:
            UIWindowSceneSessionRoleApplication:
              - UISceneConfigurationName: Default Configuration
                UISceneDelegateClassName: "{scene_delegate}"
'''
    orientation_names = {"portrait": "UIInterfaceOrientationPortrait", "portrait_upside_down": "UIInterfaceOrientationPortraitUpsideDown", "landscape_left": "UIInterfaceOrientationLandscapeLeft", "landscape_right": "UIInterfaceOrientationLandscapeRight"}
    orientations = config.get("supported_orientations", [])
    if orientations:
        values = " ".join(orientation_names[value] for value in orientations)
        if config["ui"] == "swiftui":
            generated_info_setting += f'        INFOPLIST_KEY_UISupportedInterfaceOrientations: "{values}"\n'
        else:
            info_section += "        UISupportedInterfaceOrientations: [" + ", ".join(orientation_names[value] for value in orientations) + "]\n"
    return f"name: {name}\noptions:\n  deploymentTarget:\n    iOS: \"{config['deployment_target']}\"\n  developmentLanguage: {config['default_localization']}\nsettings:\n  base:\n    MARKETING_VERSION: \"{config['marketing_version']}\"\n    CURRENT_PROJECT_VERSION: \"{config['build_number']}\"\ntargets:\n  {name}:\n    type: application\n    platform: iOS\n    sources: [App]\n{info_section}    settings:\n      base:\n        PRODUCT_MODULE_NAME: {name}AppModule\n        PRODUCT_BUNDLE_IDENTIFIER: {bundle_id}\n        TARGETED_DEVICE_FAMILY: \"{device_family}\"\n        CODE_SIGN_STYLE: {config['code_sign_style'].capitalize()}\n{team_setting}{swift_setting}        SWIFT_TREAT_WARNINGS_AS_ERRORS: {warnings}\n        GCC_TREAT_WARNINGS_AS_ERRORS: {warnings}\n{generated_info_setting}{test_lines}"


def _privacy_manifest() -> str:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\"><dict><key>NSPrivacyTracking</key><false/><key>NSPrivacyCollectedDataTypes</key><array/><key>NSPrivacyAccessedAPITypes</key><array/></dict></plist>\n"


def _test_sources(name: str, language: str) -> Dict[str, str]:
    if language == "objc":
        return {f"Tests/{name}Tests.m": "#import <XCTest/XCTest.h>\n\n@interface AppTests : XCTestCase\n@end\n\n@implementation AppTests\n// TODO: 根据真实业务场景补充首页验收测试。\n@end\n"}
    return {f"Tests/{name}Tests.swift": "import XCTest\n\nfinal class AppTests: XCTestCase {\n    // TODO: 根据真实业务场景补充首页验收测试。\n}\n"}


def _ui_test_sources(name: str, language: str) -> Dict[str, str]:
    if language == "objc":
        return {f"UITests/{name}UITests.m": "#import <XCTest/XCTest.h>\n\n@interface AppUITests : XCTestCase\n@end\n\n@implementation AppUITests\n// TODO: 根据真实用户路径补充启动和首页 UI 测试。\n@end\n"}
    return {f"UITests/{name}UITests.swift": "import XCTest\n\nfinal class AppUITests: XCTestCase {\n    // TODO: 根据真实用户路径补充启动和首页 UI 测试。\n}\n"}


def _strings_literal(value: str) -> str:
    """转义 Apple .strings 文件中的键和值。"""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def _validate_output_paths(output: Path, sources: Dict[str, str]) -> None:
    """Validate the entire render plan before creating files or directories."""
    root = output.resolve()
    seen = set()
    reserved = {".ios-workflow", ".agents", ".git", "AGENTS.md", ".gitignore"}
    for relative in sources:
        path = PurePosixPath(relative)
        if (not path.parts or path.is_absolute() or PureWindowsPath(relative).drive
                or ".." in path.parts or "\\" in relative or "\x00" in relative
                or path.as_posix() != relative or path.parts[0] in reserved):
            raise ConfigurationError(f"生成路径必须位于项目内且不得覆盖接入记录: {relative!r}")
        if relative.casefold() in seen:
            raise ConfigurationError(f"生成路径重复（不区分大小写）: {relative!r}")
        seen.add(relative.casefold())
        destination = root / relative
        if not destination.resolve().is_relative_to(root):
            raise ConfigurationError(f"生成路径越过项目目录: {relative!r}")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"生成路径已存在，不覆盖: {relative!r}")


def _write_generated_sources(output: Path, sources: Dict[str, str]) -> List[Path]:
    """Create files exclusively, keeping traversal anchored to the project fd."""
    _validate_output_paths(output, sources)
    output.mkdir(parents=True, exist_ok=True)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root_fd = os.open(output, directory_flags)
    try:
        for relative, content in sources.items():
            parts = PurePosixPath(relative).parts
            parent_fd = os.dup(root_fd)
            try:
                for component in parts[:-1]:
                    try:
                        os.mkdir(component, dir_fd=parent_fd)
                    except FileExistsError:
                        pass
                    next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
                    os.close(parent_fd)
                    parent_fd = next_fd
                file_fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o644, dir_fd=parent_fd)
                with os.fdopen(file_fd, "w", encoding="utf-8") as stream:
                    stream.write(content)
            finally:
                os.close(parent_fd)
    finally:
        os.close(root_fd)
    return sorted(output / relative for relative in sources)


def generate_project(instance_path: Path, output: Path, *, allow_project_records: bool = False) -> List[Path]:
    """生成骨架；显式允许项目内已有需求记录，但绝不覆盖业务文件。"""
    instance = load_project_instance(instance_path)
    project_name = instance["project_name"]
    config = instance["config"]
    tokens = instance["design_tokens"]
    name = _swift_name(project_name)
    skill_root = Path(__file__).resolve().parents[1]
    if output.resolve() == skill_root or skill_root in output.resolve().parents:
        raise ConfigurationError("业务项目不能生成在 Skill 目录内")
    if output.exists():
        entries = list(output.iterdir())
        # 首次生成前可能已经接入 Skill 或通过 Git 同步需求记录。
        # 生成文件不会使用这些保留名称，所有业务文件仍然拒绝覆盖。
        def is_setup_metadata(path: Path) -> bool:
            if path.is_symlink():
                return False
            if path.name in (".ios-workflow", ".agents"):
                return path.is_dir()
            if path.name in ("AGENTS.md", ".gitignore"):
                return path.is_file()
            if path.name == ".git":
                return path.is_dir() or path.is_file()
            return False

        records_only = allow_project_records and all(is_setup_metadata(path) for path in entries)
        if entries and not records_only:
            raise FileExistsError(f"输出目录必须为空或仅包含显式允许的项目记录: {output}")
    manual_appearance = config["supports_manual_dark_mode_switch"]
    sources = _swiftui_sources(name, config["comment_level"], config["architecture"], config["navigation_enabled"], manual_appearance) if config["ui"] == "swiftui" else (_swift_uikit_sources(name, config["comment_level"], config["architecture"], config["navigation_enabled"], manual_appearance) if config["language"] == "swift" else _objc_sources(config["objc_class_prefix"], config["comment_level"], config["architecture"], config["navigation_enabled"], manual_appearance))
    if config["language"] == "swift":
        sources["App/Core/Localization/LocalizationPolicy.swift"] = _swift_localization_policy(config["comment_level"])
    else:
        sources.update(_objc_localization_policy(config["objc_class_prefix"], config["comment_level"]))
    for path, content in list(sources.items()):
        sources[path] = content.replace("__LANGUAGE_MODE__", config["default_language_mode"]).replace("__DEFAULT_LOCALIZATION__", config["default_localization"])
    if config["language"] == "swift":
        sources["App/DesignSystem/DesignTokens.swift"] = render_swift_design_tokens(tokens, config["ui"], config["comment_level"])
    else:
        header, implementation = render_objc_design_tokens(tokens, config["comment_level"])
        sources["App/DesignSystem/DesignTokens.h"] = header
        sources["App/DesignSystem/DesignTokens.m"] = implementation
    if config["include_unit_tests"]:
        sources.update(_test_sources(name, config["language"]))
    if config["include_ui_tests"]:
        sources.update(_ui_test_sources(name, config["language"]))
    sources["project.yml"] = _project_yml(name, config)
    if config["generate_privacy_manifest"]:
        sources["App/Resources/PrivacyInfo.xcprivacy"] = _privacy_manifest()
    for locale in config["supported_localizations"]:
        lines = [
            f'"{_strings_literal(key)}" = "{_strings_literal(translations[locale])}";'
            for key, translations in config["localization_strings"].items()
        ]
        sources[f"App/Resources/{locale}.lproj/Localizable.strings"] = "\n".join(lines) + "\n"
    manager = config["dependency_manager"]
    if manager == "pod":
        sources["Podfile"] = f"platform :ios, '{config['deployment_target']}'\n\ntarget '{name}' do\n  # 按需添加使用精确版本的依赖。\nend\n"
    elif manager == "carthage":
        sources["Cartfile"] = "# 按需添加使用 == 固定版本的依赖。\n"
    return _write_generated_sources(output, sources)


def generate_xcodeproj(project_dir: Path) -> Path:
    """在 XcodeGen 可用时生成工程；缺失时明确失败，不改写 project.yml。"""
    executable = shutil.which("xcodegen")
    if not executable:
        raise RuntimeError("未安装 XcodeGen，已保留 project.yml")
    subprocess.run([executable, "generate"], cwd=project_dir, check=True, capture_output=True, text=True)
    projects = sorted(project_dir.glob("*.xcodeproj"))
    if len(projects) != 1:
        raise RuntimeError("XcodeGen 未生成唯一的 .xcodeproj")
    return projects[0]


def install_dependencies(project_dir: Path, manager: str, project: Path) -> str:
    """按配置安装或解析依赖；工具缺失或执行失败时由调用方停止后续编译。"""
    if manager == "none":
        return "未配置三方依赖"
    commands = {
        "pod": ("pod", ["pod", "install"]),
        "spm": ("xcodebuild", ["xcodebuild", "-resolvePackageDependencies", "-project", project.name]),
        "carthage": ("carthage", ["carthage", "bootstrap", "--use-xcframeworks"]),
    }
    if manager not in commands:
        raise ConfigurationError(f"不支持的依赖管理器: {manager}")
    tool, command = commands[manager]
    executable = shutil.which(tool)
    if not executable:
        raise RuntimeError(f"未安装 {tool}，不能完成 {manager} 依赖准备")
    command[0] = executable
    subprocess.run(command, cwd=project_dir, check=True, capture_output=True, text=True)
    return f"{manager} 依赖准备完成"


def materialize_project(instance_path: Path, output: Path, *, allow_project_records: bool = False) -> Dict[str, Any]:
    """完成项目文件、Xcode 工程及依赖准备，返回可用于后续编译的摘要。"""
    config = load_project_instance(instance_path)["config"]
    if not config["generate_xcodeproj"] and config["dependency_manager"] != "none":
        raise ConfigurationError("关闭 generate_xcodeproj 时不能自动准备依赖")
    files = generate_project(instance_path, output, allow_project_records=allow_project_records)
    if not config["generate_xcodeproj"]:
        if config["dependency_manager"] != "none":
            raise ConfigurationError("关闭 generate_xcodeproj 时不能自动准备依赖")
        return {"files": files, "project": None, "dependencies": "未配置三方依赖"}
    project = generate_xcodeproj(output)
    dependency_status = install_dependencies(output, config["dependency_manager"], project)
    return {"files": files, "project": project, "dependencies": dependency_status}
