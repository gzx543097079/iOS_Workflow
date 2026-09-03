import Foundation

enum LocalizationPolicy {
    static let didChangeNotification = Notification.Name("LocalizationPolicyDidChange")

    private static let preferenceStore = LanguagePreferenceStore()

    static var selectedLanguage: AppLanguage {
        preferenceStore.selectedLanguage
    }

    // 使用成员选择的资源包解析文案；资源不可用时安全回退系统语言。
    static func localized(_ key: String) -> String {
        guard let resourceCode = selectedLanguage.resourceCode,
              let path = Bundle.main.path(forResource: resourceCode, ofType: "lproj"),
              let bundle = Bundle(path: path) else {
            return NSLocalizedString(key, comment: "")
        }
        return bundle.localizedString(forKey: key, value: nil, table: nil)
    }

    // 仅在选择真实变化时通知页面刷新，避免无意义的重复渲染。
    static func select(_ language: AppLanguage) {
        guard language != selectedLanguage else { return }
        preferenceStore.selectedLanguage = language
        NotificationCenter.default.post(name: didChangeNotification, object: nil)
    }
}
