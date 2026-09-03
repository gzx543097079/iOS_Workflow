import UIKit

// 关于页面展示可离线获取的产品简介和当前版本。
final class AboutViewController: UIViewController {
    private let nameLabel = UILabel()
    private let descriptionLabel = UILabel()
    private let versionLabel = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        configureHierarchy()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(localizationDidChange),
            name: LocalizationPolicy.didChangeNotification,
            object: nil
        )
        render()
    }

    private func configureHierarchy() {
        view.backgroundColor = DesignTokens.Colors.background
        nameLabel.font = .preferredFont(forTextStyle: DesignTokens.Typography.title)
        nameLabel.adjustsFontForContentSizeCategory = true
        nameLabel.textAlignment = .center

        descriptionLabel.font = .preferredFont(forTextStyle: DesignTokens.Typography.body)
        descriptionLabel.adjustsFontForContentSizeCategory = true
        descriptionLabel.textColor = DesignTokens.Colors.secondaryText
        descriptionLabel.numberOfLines = 0
        descriptionLabel.textAlignment = .center
        descriptionLabel.accessibilityIdentifier = "about.description"

        versionLabel.font = .preferredFont(forTextStyle: DesignTokens.Typography.caption)
        versionLabel.adjustsFontForContentSizeCategory = true
        versionLabel.textColor = DesignTokens.Colors.secondaryText
        versionLabel.textAlignment = .center
        versionLabel.accessibilityIdentifier = "about.version"

        let stack = UIStackView(arrangedSubviews: [nameLabel, descriptionLabel, versionLabel])
        stack.axis = .vertical
        stack.spacing = DesignTokens.Spacing.lg
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)

        let safeArea = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: safeArea.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: safeArea.centerYAnchor),
            stack.leadingAnchor.constraint(greaterThanOrEqualTo: safeArea.leadingAnchor, constant: DesignTokens.contentMargin),
            stack.trailingAnchor.constraint(lessThanOrEqualTo: safeArea.trailingAnchor, constant: -DesignTokens.contentMargin),
            stack.widthAnchor.constraint(lessThanOrEqualToConstant: DesignTokens.contentMaxWidth)
        ])
    }

    // 版本号来自构建配置，缺失时显示占位符而不暴露内部构建错误。
    private func render() {
        title = LocalizationPolicy.localized("about.title")
        nameLabel.text = LocalizationPolicy.localized("home.title")
        descriptionLabel.text = LocalizationPolicy.localized("about.description")
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "–"
        versionLabel.text = String(
            format: LocalizationPolicy.localized("about.version"),
            locale: Locale.current,
            version
        )
    }

    @objc private func localizationDidChange() {
        render()
    }
}
