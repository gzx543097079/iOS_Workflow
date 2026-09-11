// Optional template: copy into the project's existing UI-test target and adapt its ready marker.
// Capturing an attachment is only an input to visual_snapshot.swift, not a visual pass.
import XCTest

final class VisualCaptureTests: XCTestCase {
    @MainActor
    func test_captureHomeEnglishLightLarge() {
        continueAfterFailure = false
        XCUIDevice.shared.orientation = .portrait
        let app = XCUIApplication()
        app.launchArguments += [
            "-AppleLanguages", "(en)", "-AppleLocale", "en_US",
            "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryL"
        ]
        // Add the project's existing deterministic data/clock/network setup here.
        // Set simulator appearance with simctl before launch; record actual capture settings.
        app.launch()
        let ready = app.otherElements["REPLACE_WITH_PROJECT_READY_MARKER"]
        XCTAssertTrue(ready.waitForExistence(timeout: 10), "Page must reach a stable, testable state")
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "home-en-light-large"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
