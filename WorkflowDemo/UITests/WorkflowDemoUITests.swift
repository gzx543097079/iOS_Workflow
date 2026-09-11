import XCTest

final class WorkflowDemoUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments += ["--ui-testing-reset", "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
    }

    func test_incrementAndReset_updatesCounter() {
        let counter = app.staticTexts["counter.value"]
        let incrementButton = app.buttons["counter.increment"]
        let resetButton = app.buttons["counter.reset"]

        for _ in 0..<4 where !incrementButton.isHittable { app.swipeUp() }

        XCTAssertEqual(counter.label, "Count: 0")
        XCTAssertFalse(resetButton.isEnabled)

        incrementButton.tap()

        XCTAssertEqual(counter.label, "Count: 1")
        XCTAssertTrue(resetButton.isEnabled)

        resetButton.tap()

        XCTAssertEqual(counter.label, "Count: 0")
        XCTAssertFalse(resetButton.isEnabled)
    }

    func test_storefrontCategoryAndProductDetails() {
        XCTAssertTrue(app.buttons["shop.product.headphones"].exists)
        app.buttons["shop.category.living"].tap()
        XCTAssertFalse(app.buttons["shop.product.headphones"].exists)
        let lamp = app.buttons["shop.product.lamp"]
        XCTAssertTrue(lamp.exists)
        lamp.tap()
        XCTAssertTrue(app.alerts["Bedside lamp"].waitForExistence(timeout: 3))
        app.alerts.buttons["Close"].tap()
        app.buttons["shop.category.all"].tap()
        XCTAssertTrue(app.buttons["shop.product.headphones"].exists)
    }

    func test_storefrontSearchShowsEmptyAndMatchingResults() {
        let search = app.searchFields.firstMatch
        search.tap()
        search.typeText("zzzz")
        XCTAssertTrue(app.staticTexts["shop.empty"].exists)
        search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: 4) + "lamp")
        XCTAssertTrue(app.buttons["shop.product.lamp"].exists)
        XCTAssertFalse(app.buttons["shop.product.headphones"].exists)
    }

    func test_changeLanguage_updatesVisibleInterface() {
        app.buttons["home.settings"].tap()
        app.cells["settings.language"].tap()

        app.cells["language.zh-Hans"].tap()

        XCTAssertTrue(app.navigationBars["语言"].exists)
        app.navigationBars["语言"].buttons.firstMatch.tap()
        XCTAssertTrue(app.navigationBars["设置"].exists)
        app.navigationBars["设置"].buttons.firstMatch.tap()
        XCTAssertTrue(app.staticTexts["工作流演示"].exists)
    }

    func test_openAbout_showsDescriptionAndVersion() {
        app.buttons["home.settings"].tap()
        app.cells["settings.about"].tap()

        XCTAssertTrue(app.navigationBars["About Us"].exists)
        XCTAssertTrue(app.staticTexts["about.description"].exists)
        XCTAssertEqual(app.staticTexts["about.version"].label, "Version 1.0")
    }
}
