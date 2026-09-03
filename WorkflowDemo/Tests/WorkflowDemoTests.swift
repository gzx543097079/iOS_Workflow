import XCTest
@testable import WorkflowDemoAppModule

final class HomeViewModelTests: XCTestCase {
    func test_init_usesZeroCount() {
        let viewModel = HomeViewModel()

        XCTAssertEqual(viewModel.count, 0)
    }

    func test_increment_addsOne() {
        var viewModel = HomeViewModel()

        viewModel.increment()

        XCTAssertEqual(viewModel.count, 1)
    }

    func test_increment_whenAtMaximum_keepsMaximumValue() {
        var viewModel = HomeViewModel(count: .max)

        viewModel.increment()

        XCTAssertEqual(viewModel.count, .max)
    }

    func test_reset_whenCountIsPositive_restoresZero() {
        var viewModel = HomeViewModel(count: 3)

        viewModel.reset()

        XCTAssertEqual(viewModel.count, 0)
    }
}

final class LanguagePreferenceStoreTests: XCTestCase {
    private var userDefaults: UserDefaults!
    private var suiteName: String!

    override func setUp() {
        super.setUp()
        suiteName = "WorkflowDemoTests.LanguagePreferenceStore.\(UUID().uuidString)"
        userDefaults = UserDefaults(suiteName: suiteName)
    }

    override func tearDown() {
        userDefaults.removePersistentDomain(forName: suiteName)
        userDefaults = nil
        suiteName = nil
        super.tearDown()
    }

    func test_selectedLanguage_withoutSavedValue_usesSystem() {
        let store = LanguagePreferenceStore(userDefaults: userDefaults)

        XCTAssertEqual(store.selectedLanguage, .system)
    }

    func test_selectedLanguage_afterSaving_returnsSelection() {
        let store = LanguagePreferenceStore(userDefaults: userDefaults)

        store.selectedLanguage = .simplifiedChinese

        XCTAssertEqual(store.selectedLanguage, .simplifiedChinese)
    }

    func test_selectedLanguage_withInvalidSavedValue_fallsBackToSystem() {
        userDefaults.set("unsupported", forKey: LanguagePreferenceStore.storageKey)
        let store = LanguagePreferenceStore(userDefaults: userDefaults)

        XCTAssertEqual(store.selectedLanguage, .system)
    }
}
