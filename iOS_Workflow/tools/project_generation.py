"""校验工作流配置并生成可复现的最小 iOS 项目骨架。"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


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


def _require_choice(config: Dict[str, Any], key: str, choices: Iterable[str]) -> str:
    value = config.get(key)
    allowed = tuple(choices)
    if value not in allowed:
        raise ConfigurationError(f"{key} 必须是 {', '.join(allowed)} 之一")
    return str(value)


def validate_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证项目默认配置以及不受支持的技术组合。"""
    language = _require_choice(config, "language", ("swift", "objc"))
    ui = _require_choice(config, "ui", ("uikit", "swiftui"))
    _require_choice(config, "architecture", ("mvvm", "mvc"))
    _require_choice(config, "dependency_manager", ("pod", "spm", "carthage", "none"))
    _require_choice(config, "default_language_mode", ("system", "fixed"))
    _require_choice(config, "test_framework", ("xctest",))
    _require_choice(config, "strict_concurrency", ("minimal", "targeted", "complete"))
    _require_choice(config, "code_sign_style", ("automatic", "manual"))
    if language == "objc" and ui == "swiftui":
        raise ConfigurationError("Objective-C 项目不支持 SwiftUI，请选择 UIKit 或 Swift")
    if not re.fullmatch(r"\d+\.\d+", str(config.get("deployment_target", ""))):
        raise ConfigurationError("deployment_target 必须是 major.minor")
    if not re.fullmatch(r"\d+\.\d+", str(config.get("swift_version", ""))):
        raise ConfigurationError("swift_version 必须是 major.minor")
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", str(config.get("marketing_version", ""))):
        raise ConfigurationError("marketing_version 必须是数字版本")
    if not str(config.get("build_number", "")).isdigit():
        raise ConfigurationError("build_number 必须是正整数字符串")
    if config.get("comment_level") not in (1, 2, 3, 4):
        raise ConfigurationError("comment_level 必须是 1 到 4")
    if not re.fullmatch(r"[A-Z]{2,3}", str(config.get("objc_class_prefix", ""))):
        raise ConfigurationError("objc_class_prefix 必须是 2–3 个大写字母")
    localizations = config.get("supported_localizations")
    if not isinstance(localizations, list) or not localizations or not all(isinstance(x, str) and x for x in localizations):
        raise ConfigurationError("supported_localizations 必须是非空字符串数组")
    if config.get("default_localization") not in localizations:
        raise ConfigurationError("default_localization 必须包含在 supported_localizations 中")
    devices = config.get("target_devices")
    if not isinstance(devices, list) or not devices or not set(devices).issubset({"iphone", "ipad"}):
        raise ConfigurationError("target_devices 只能包含 iphone、ipad")
    for key in ("navigation_enabled", "include_unit_tests", "include_ui_tests", "warnings_as_errors", "generate_privacy_manifest", "generate_xcodeproj"):
        if not isinstance(config.get(key), bool):
            raise ConfigurationError(f"{key} 必须是布尔值")
    prefix = str(config.get("bundle_id_prefix", ""))
    bundle_id = str(config.get("bundle_id", ""))
    identifier_pattern = r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
    if not re.fullmatch(identifier_pattern, prefix):
        raise ConfigurationError("bundle_id_prefix 必须是反向域名格式")
    if bundle_id and not re.fullmatch(identifier_pattern, bundle_id):
        raise ConfigurationError("bundle_id 必须为空或使用反向域名格式")
    return dict(config)


def validate_design_tokens(tokens: Dict[str, Any]) -> Dict[str, Any]:
    """验证生成代码需要的 DesignTokens 字段和数值。"""
    maps = ("spacing", "radius", "control_height", "icon_size", "border_width", "opacity", "animation_duration")
    for key in maps:
        value = tokens.get(key)
        if not isinstance(value, dict) or not value:
            raise ConfigurationError(f"DesignTokens.{key} 必须是非空对象")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value.values()):
            raise ConfigurationError(f"DesignTokens.{key} 只能包含数字")
    for key in ("content_margin", "content_max_width", "minimum_tap_target"):
        if not isinstance(tokens.get(key), (int, float)) or isinstance(tokens.get(key), bool):
            raise ConfigurationError(f"DesignTokens.{key} 必须是数字")
    for key in ("typography", "colors"):
        value = tokens.get(key)
        if not isinstance(value, dict) or not value or not all(isinstance(v, str) and v for v in value.values()):
            raise ConfigurationError(f"DesignTokens.{key} 必须是非空字符串对象")
    supported_text_styles = {"largeTitle", "title", "title2", "title3", "headline", "subheadline", "body", "callout", "footnote", "caption", "caption2"}
    if not set(tokens["typography"].values()).issubset(supported_text_styles):
        raise ConfigurationError("DesignTokens.typography 包含不支持的系统文字样式")
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


def _swift_uikit_sources(name: str, level: int, architecture: str, navigation_enabled: bool) -> Dict[str, str]:
    page_comment = _comment(level, "首页展示应用的基础内容，并作为后续业务模块的入口。")
    method_comment = _comment(level, "集中创建视图层级和约束，避免初始化流程散落在生命周期方法中。", "    ") if level >= 3 else ""
    root = "UINavigationController(rootViewController: HomeViewController())" if navigation_enabled else "HomeViewController()"
    view_model_property = "    private let viewModel = HomeViewModel()\n" if architecture == "mvvm" else ""
    title_key = "viewModel.titleKey" if architecture == "mvvm" else '"home.title"'
    sources = {
        "App/AppDelegate.swift": "import UIKit\n\n@main\nfinal class AppDelegate: UIResponder, UIApplicationDelegate {\n    func application(_ application: UIApplication, configurationForConnecting connectingSceneSession: UISceneSession, options: UIScene.ConnectionOptions) -> UISceneConfiguration {\n        UISceneConfiguration(name: \"Default Configuration\", sessionRole: connectingSceneSession.role)\n    }\n}\n",
        "App/SceneDelegate.swift": f"import UIKit\n\nfinal class SceneDelegate: UIResponder, UIWindowSceneDelegate {{\n    var window: UIWindow?\n\n    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {{\n        guard let windowScene = scene as? UIWindowScene else {{ return }}\n        let window = UIWindow(windowScene: windowScene)\n        window.rootViewController = {root}\n        window.makeKeyAndVisible()\n        self.window = window\n    }}\n}}\n",
        "App/Features/Home/HomeViewController.swift": f"import UIKit\n\n{page_comment}final class HomeViewController: UIViewController {{\n{view_model_property}    private let titleLabel = UILabel()\n\n    override func viewDidLoad() {{\n        super.viewDidLoad()\n        configureHierarchy()\n    }}\n\n{method_comment}    private func configureHierarchy() {{\n        view.backgroundColor = DesignTokens.Colors.background\n        titleLabel.text = LocalizationPolicy.localized({title_key})\n        titleLabel.font = .preferredFont(forTextStyle: .title2)\n        titleLabel.translatesAutoresizingMaskIntoConstraints = false\n        view.addSubview(titleLabel)\n        NSLayoutConstraint.activate([\n            titleLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),\n            titleLabel.centerYAnchor.constraint(equalTo: view.centerYAnchor)\n        ])\n    }}\n}}\n",
    }
    if architecture == "mvvm":
        sources["App/Features/Home/HomeViewModel.swift"] = _swift_view_model(level)
    return sources


def _swiftui_sources(name: str, level: int, architecture: str, navigation_enabled: bool) -> Dict[str, str]:
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
    sources = {
        f"App/{name}App.swift": f"import SwiftUI\n\n@main\nstruct {name}App: App {{\n    var body: some Scene {{\n        WindowGroup {{\n            HomeView()\n        }}\n    }}\n}}\n",
        "App/Features/Home/HomeView.swift": f"import SwiftUI\n\n{comment}struct HomeView: View {{\n{view_model_property}    var body: some View {{\n        {content}\n    }}\n}}\n",
    }
    if architecture == "mvvm":
        sources["App/Features/Home/HomeViewModel.swift"] = _swift_view_model(level)
    return sources


def _objc_sources(prefix: str, level: int, architecture: str, navigation_enabled: bool) -> Dict[str, str]:
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
    sources = {
        "App/main.m": f"#import <UIKit/UIKit.h>\n#import \"{app_delegate}.h\"\n\nint main(int argc, char * argv[]) {{\n    @autoreleasepool {{\n        return UIApplicationMain(argc, argv, nil, NSStringFromClass({app_delegate}.class));\n    }}\n}}\n",
        f"App/{app_delegate}.h": f"#import <UIKit/UIKit.h>\n\n@interface {app_delegate} : UIResponder <UIApplicationDelegate>\n@end\n",
        f"App/{app_delegate}.m": f"#import \"{app_delegate}.h\"\n\n@implementation {app_delegate}\n- (UISceneConfiguration *)application:(UIApplication *)application configurationForConnectingSceneSession:(UISceneSession *)connectingSceneSession options:(UISceneConnectionOptions *)options {{\n    return [[UISceneConfiguration alloc] initWithName:@\"Default Configuration\" sessionRole:connectingSceneSession.role];\n}}\n@end\n",
        f"App/{scene_delegate}.h": f"#import <UIKit/UIKit.h>\n\n@interface {scene_delegate} : UIResponder <UIWindowSceneDelegate>\n@property (nonatomic, strong) UIWindow *window;\n@end\n",
        f"App/{scene_delegate}.m": f"#import \"{scene_delegate}.h\"\n#import \"{home}.h\"\n\n@implementation {scene_delegate}\n- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)connectionOptions {{\n    if (![scene isKindOfClass:UIWindowScene.class]) {{ return; }}\n    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];\n    self.window.rootViewController = {root};\n    [self.window makeKeyAndVisible];\n}}\n@end\n",
        f"App/Features/Home/{home}.h": f"#import <UIKit/UIKit.h>\n\n{page_comment}@interface {home} : UIViewController\n@end\n",
        f"App/Features/Home/{home}.m": f"#import \"{home}.h\"\n#import \"DesignTokens.h\"\n#import \"{prefix}LocalizationPolicy.h\"\n{model_header}\n@interface {home} ()\n{model_property}@property (nonatomic, strong) UILabel *titleLabel;\n@end\n\n@implementation {home}\n- (void)viewDidLoad {{\n    [super viewDidLoad];\n{model_setup}    [self configureHierarchy];\n}}\n\n{method_comment}- (void)configureHierarchy {{\n    self.view.backgroundColor = [DesignTokens colorBackground];\n    self.titleLabel = [UILabel new];\n    self.titleLabel.text = [{prefix}LocalizationPolicy localizedStringForKey:{title_key}];\n    self.titleLabel.translatesAutoresizingMaskIntoConstraints = NO;\n    [self.view addSubview:self.titleLabel];\n    [NSLayoutConstraint activateConstraints:@[[self.titleLabel.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor], [self.titleLabel.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor]]];\n}}\n@end\n",
    }
    if architecture == "mvvm":
        model_comment = page_comment.replace("首页展示应用的基础内容，并作为后续业务模块的入口。", "首页 Model 保存展示所需的本地化键，避免视图直接持有业务文案。")
        sources[f"App/Features/Home/{prefix}HomeViewModel.h"] = f"#import <Foundation/Foundation.h>\n\n{model_comment}@interface {prefix}HomeViewModel : NSObject\n@property (nonatomic, copy, readonly) NSString *titleKey;\n@end\n"
        sources[f"App/Features/Home/{prefix}HomeViewModel.m"] = f"#import \"{prefix}HomeViewModel.h\"\n\n@implementation {prefix}HomeViewModel\n- (NSString *)titleKey {{ return @\"home.title\"; }}\n@end\n"
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
    scene_setting = "        INFOPLIST_KEY_UIApplicationSceneManifest_Generation: YES\n" if config["ui"] == "uikit" else ""
    return f"name: {name}\noptions:\n  deploymentTarget:\n    iOS: \"{config['deployment_target']}\"\n  developmentLanguage: {config['default_localization']}\nsettings:\n  base:\n    MARKETING_VERSION: \"{config['marketing_version']}\"\n    CURRENT_PROJECT_VERSION: \"{config['build_number']}\"\ntargets:\n  {name}:\n    type: application\n    platform: iOS\n    sources: [App]\n    settings:\n      base:\n        PRODUCT_MODULE_NAME: {name}AppModule\n        PRODUCT_BUNDLE_IDENTIFIER: {bundle_id}\n        TARGETED_DEVICE_FAMILY: \"{device_family}\"\n        CODE_SIGN_STYLE: {config['code_sign_style'].capitalize()}\n{team_setting}{swift_setting}        SWIFT_TREAT_WARNINGS_AS_ERRORS: {warnings}\n        GCC_TREAT_WARNINGS_AS_ERRORS: {warnings}\n        GENERATE_INFOPLIST_FILE: YES\n        INFOPLIST_KEY_UILaunchScreen_Generation: YES\n{scene_setting}{test_lines}"


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


def generate_project(defaults_path: Path, tokens_path: Path, output: Path, project_name: str) -> List[Path]:
    """在空目录生成项目骨架，返回生成文件列表。"""
    config = validate_defaults(load_jsonc(defaults_path))
    tokens = validate_design_tokens(load_jsonc(tokens_path))
    name = _swift_name(project_name)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"输出目录必须为空: {output}")
    output.mkdir(parents=True, exist_ok=True)
    sources = _swiftui_sources(name, config["comment_level"], config["architecture"], config["navigation_enabled"]) if config["ui"] == "swiftui" else (_swift_uikit_sources(name, config["comment_level"], config["architecture"], config["navigation_enabled"]) if config["language"] == "swift" else _objc_sources(config["objc_class_prefix"], config["comment_level"], config["architecture"], config["navigation_enabled"]))
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
    sources["workflow.json"] = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    if config["generate_privacy_manifest"]:
        sources["App/Resources/PrivacyInfo.xcprivacy"] = _privacy_manifest()
    for locale in config["supported_localizations"]:
        title = "首页" if locale.startswith("zh") else "Home"
        sources[f"App/Resources/{locale}.lproj/Localizable.strings"] = f'"home.title" = "{title}";\n'
    manager = config["dependency_manager"]
    if manager == "pod":
        sources["Podfile"] = f"platform :ios, '{config['deployment_target']}'\n\ntarget '{name}' do\n  # 按需添加使用精确版本的依赖。\nend\n"
    elif manager == "carthage":
        sources["Cartfile"] = "# 按需添加使用 == 固定版本的依赖。\n"
    generated: List[Path] = []
    for relative, content in sources.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        generated.append(destination)
    return sorted(generated)


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


def materialize_project(defaults_path: Path, tokens_path: Path, output: Path, project_name: str) -> Dict[str, Any]:
    """完成项目文件、Xcode 工程及依赖准备，返回可用于后续编译的摘要。"""
    config = validate_defaults(load_jsonc(defaults_path))
    files = generate_project(defaults_path, tokens_path, output, project_name)
    if not config["generate_xcodeproj"]:
        if config["dependency_manager"] != "none":
            raise ConfigurationError("关闭 generate_xcodeproj 时不能自动准备依赖")
        return {"files": files, "project": None, "dependencies": "未配置三方依赖"}
    project = generate_xcodeproj(output)
    dependency_status = install_dependencies(output, config["dependency_manager"], project)
    return {"files": files, "project": project, "dependencies": dependency_status}
