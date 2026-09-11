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

final class StorefrontViewModelTests: XCTestCase {
    func test_searchAndCategory_applyTogether() {
        var model = StorefrontViewModel()
        model.category = "digital"
        model.query = "lamp"
        XCTAssertTrue(model.filteredProducts(localize: { $0 }).isEmpty)
        model.category = "living"
        XCTAssertEqual(model.filteredProducts(localize: { $0 }).map(\.id), ["lamp"])
    }

    func test_search_trimsWhitespaceAndIgnoresCase() {
        var model = StorefrontViewModel()
        model.query = "  HEADPHONES\n"
        XCTAssertEqual(model.filteredProducts(localize: { $0 }).map(\.id), ["headphones"])
    }

    func test_search_usesLocalizedProductName() {
        var model = StorefrontViewModel()
        model.query = "耳机"
        XCTAssertEqual(model.filteredProducts(localize: { $0 == "shop.product.headphones" ? "无线耳机" : "其他" }).map(\.id), ["headphones"])
    }

    func test_whitespaceQuery_keepsSelectedCategory() {
        var model = StorefrontViewModel()
        model.category = "living"
        model.query = " \n"
        XCTAssertEqual(model.filteredProducts(localize: { $0 }).map(\.id), ["lamp", "mug"])
    }
}
