import UIKit

// 设置页集中提供应用级偏好和产品信息入口。
final class SettingsViewController: UITableViewController {
    private enum Section: Int, CaseIterable {
        case preferences
        case information
    }

    init() {
        super.init(style: .insetGrouped)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(localizationDidChange),
            name: LocalizationPolicy.didChangeNotification,
            object: nil
        )
        render()
    }

    override func numberOfSections(in tableView: UITableView) -> Int {
        Section.allCases.count
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        1
    }

    override func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        guard let section = Section(rawValue: section) else { return nil }
        switch section {
        case .preferences: return LocalizationPolicy.localized("settings.general")
        case .information: return LocalizationPolicy.localized("settings.information")
        }
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = UITableViewCell(style: .value1, reuseIdentifier: nil)
        cell.accessoryType = .disclosureIndicator
        cell.textLabel?.font = .preferredFont(forTextStyle: DesignTokens.Typography.body)
        cell.textLabel?.adjustsFontForContentSizeCategory = true
        cell.detailTextLabel?.font = .preferredFont(forTextStyle: DesignTokens.Typography.caption)
        cell.detailTextLabel?.adjustsFontForContentSizeCategory = true

        switch Section(rawValue: indexPath.section) {
        case .preferences:
            cell.textLabel?.text = LocalizationPolicy.localized("settings.language")
            cell.detailTextLabel?.text = LocalizationPolicy.selectedLanguage.displayName
            cell.accessibilityIdentifier = "settings.language"
        case .information:
            cell.textLabel?.text = LocalizationPolicy.localized("settings.about")
            cell.accessibilityIdentifier = "settings.about"
        case .none:
            break
        }
        return cell
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        switch Section(rawValue: indexPath.section) {
        case .preferences:
            navigationController?.pushViewController(LanguageViewController(), animated: true)
        case .information:
            navigationController?.pushViewController(AboutViewController(), animated: true)
        case .none:
            break
        }
    }

    private func render() {
        title = LocalizationPolicy.localized("settings.title")
        tableView.reloadData()
    }

    @objc private func localizationDidChange() {
        render()
    }
}
