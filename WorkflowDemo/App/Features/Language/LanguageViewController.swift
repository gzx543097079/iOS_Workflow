import UIKit

// 语言页展示全部可用资源，并以勾选状态反馈当前选择。
final class LanguageViewController: UITableViewController {
    private let languages = AppLanguage.allCases

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

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        languages.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let language = languages[indexPath.row]
        let cell = UITableViewCell(style: .default, reuseIdentifier: nil)
        cell.textLabel?.text = language.displayName
        cell.textLabel?.font = .preferredFont(forTextStyle: DesignTokens.Typography.body)
        cell.textLabel?.adjustsFontForContentSizeCategory = true
        cell.accessoryType = language == LocalizationPolicy.selectedLanguage ? .checkmark : .none
        cell.accessibilityIdentifier = "language.\(language.rawValue)"
        return cell
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        LocalizationPolicy.select(languages[indexPath.row])
        tableView.reloadData()
    }

    private func render() {
        title = LocalizationPolicy.localized("language.title")
        tableView.reloadData()
    }

    @objc private func localizationDidChange() {
        render()
    }
}
