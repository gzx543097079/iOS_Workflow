import UIKit

// 首页展示应用的基础内容，并作为后续业务模块的入口。
final class HomeViewController: UIViewController {
    private var viewModel = HomeViewModel()
    private let titleLabel = UILabel()
    private let counterLabel = UILabel()
    private let incrementButton = UIButton(type: .system)
    private let resetButton = UIButton(type: .system)

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

    // 集中创建视图层级和约束，避免初始化流程散落在生命周期方法中。
    private func configureHierarchy() {
        view.backgroundColor = DesignTokens.Colors.background

        titleLabel.font = .preferredFont(forTextStyle: DesignTokens.Typography.title)
        titleLabel.adjustsFontForContentSizeCategory = true
        titleLabel.numberOfLines = 0
        titleLabel.textAlignment = .center

        counterLabel.font = .preferredFont(forTextStyle: DesignTokens.Typography.headline)
        counterLabel.adjustsFontForContentSizeCategory = true
        counterLabel.textAlignment = .center
        counterLabel.accessibilityIdentifier = "counter.value"

        configureButton(incrementButton, titleKey: viewModel.incrementKey, action: #selector(incrementCount))
        incrementButton.accessibilityIdentifier = "counter.increment"
        configureButton(resetButton, titleKey: viewModel.resetKey, action: #selector(resetCount))
        resetButton.accessibilityIdentifier = "counter.reset"

        let settingsButton = UIBarButtonItem(
            title: LocalizationPolicy.localized("home.settings"),
            style: .plain,
            target: self,
            action: #selector(showSettings)
        )
        settingsButton.accessibilityIdentifier = "home.settings"
        navigationItem.rightBarButtonItem = settingsButton

        let buttonStack = UIStackView(arrangedSubviews: [incrementButton, resetButton])
        buttonStack.axis = .vertical
        buttonStack.spacing = DesignTokens.Spacing.sm

        let contentStack = UIStackView(arrangedSubviews: [titleLabel, counterLabel, buttonStack])
        contentStack.axis = .vertical
        contentStack.spacing = DesignTokens.Spacing.xl
        contentStack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(contentStack)

        let safeArea = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            contentStack.centerXAnchor.constraint(equalTo: safeArea.centerXAnchor),
            contentStack.centerYAnchor.constraint(equalTo: safeArea.centerYAnchor),
            contentStack.leadingAnchor.constraint(greaterThanOrEqualTo: safeArea.leadingAnchor, constant: DesignTokens.contentMargin),
            contentStack.trailingAnchor.constraint(lessThanOrEqualTo: safeArea.trailingAnchor, constant: -DesignTokens.contentMargin),
            contentStack.widthAnchor.constraint(lessThanOrEqualToConstant: DesignTokens.contentMaxWidth),
            incrementButton.heightAnchor.constraint(greaterThanOrEqualToConstant: DesignTokens.minimumTapTarget),
            resetButton.heightAnchor.constraint(greaterThanOrEqualToConstant: DesignTokens.minimumTapTarget)
        ])
    }

    // 系统按钮统一使用本地化标题、Dynamic Type 和最小触控尺寸。
    private func configureButton(_ button: UIButton, titleKey: String, action: Selector) {
        button.setTitle(LocalizationPolicy.localized(titleKey), for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: DesignTokens.Typography.body)
        button.titleLabel?.adjustsFontForContentSizeCategory = true
        button.addTarget(self, action: action, for: .touchUpInside)
    }

    // 每次状态变化后集中刷新展示，避免控件状态与 ViewModel 分离。
    private func render() {
        titleLabel.text = LocalizationPolicy.localized(viewModel.titleKey)
        navigationItem.title = LocalizationPolicy.localized(viewModel.titleKey)
        counterLabel.text = String(
            format: LocalizationPolicy.localized(viewModel.counterKey),
            locale: Locale.current,
            viewModel.count
        )
        incrementButton.setTitle(LocalizationPolicy.localized(viewModel.incrementKey), for: .normal)
        resetButton.setTitle(LocalizationPolicy.localized(viewModel.resetKey), for: .normal)
        navigationItem.rightBarButtonItem?.title = LocalizationPolicy.localized("home.settings")
        resetButton.isEnabled = viewModel.count != 0
    }

    @objc private func incrementCount() {
        viewModel.increment()
        render()
    }

    @objc private func resetCount() {
        viewModel.reset()
        render()
    }

    @objc private func showSettings() {
        navigationController?.pushViewController(SettingsViewController(), animated: true)
    }

    @objc private func localizationDidChange() {
        render()
    }
}
