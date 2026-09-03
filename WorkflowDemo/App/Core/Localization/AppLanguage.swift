import Foundation

// 应用支持的语言集合与生成的本地化资源保持一致。
enum AppLanguage: String, CaseIterable {
    case system
    case simplifiedChinese = "zh-Hans"
    case traditionalChinese = "zh-Hant"
    case english = "en"
    case spanish = "es"
    case french = "fr"
    case german = "de"
    case japanese = "ja"
    case korean = "ko"
    case brazilianPortuguese = "pt-BR"
    case italian = "it"
    case arabic = "ar"
    case russian = "ru"

    var resourceCode: String? {
        self == .system ? nil : rawValue
    }

    var displayName: String {
        switch self {
        case .system: return LocalizationPolicy.localized("language.system")
        case .simplifiedChinese: return "简体中文"
        case .traditionalChinese: return "繁體中文"
        case .english: return "English"
        case .spanish: return "Español"
        case .french: return "Français"
        case .german: return "Deutsch"
        case .japanese: return "日本語"
        case .korean: return "한국어"
        case .brazilianPortuguese: return "Português (Brasil)"
        case .italian: return "Italiano"
        case .arabic: return "العربية"
        case .russian: return "Русский"
        }
    }
}
