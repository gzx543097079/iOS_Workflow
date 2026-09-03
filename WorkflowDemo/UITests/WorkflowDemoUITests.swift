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

        XCTAssertEqual(counter.label, "Count: 0")
        XCTAssertFalse(resetButton.isEnabled)

        incrementButton.tap()

        XCTAssertEqual(counter.label, "Count: 1")
        XCTAssertTrue(resetButton.isEnabled)

        resetButton.tap()

        XCTAssertEqual(counter.label, "Count: 0")
        XCTAssertFalse(resetButton.isEnabled)
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
