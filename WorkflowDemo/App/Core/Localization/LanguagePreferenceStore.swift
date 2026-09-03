import Foundation

// 将语言选择限制在单一存储边界，便于测试默认值和异常数据回退。
final class LanguagePreferenceStore {
    static let storageKey = "selectedAppLanguage"

    private let userDefaults: UserDefaults

    init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
    }

    var selectedLanguage: AppLanguage {
        get {
            guard let value = userDefaults.string(forKey: Self.storageKey),
                  let language = AppLanguage(rawValue: value) else {
                return .system
            }
            return language
        }
        set {
            userDefaults.set(newValue.rawValue, forKey: Self.storageKey)
        }
    }

    func reset() {
        userDefaults.removeObject(forKey: Self.storageKey)
    }
}
