import UIKit

// 首页展示应用的基础内容，并作为后续业务模块的入口。
final class HomeViewController: UIViewController, UISearchBarDelegate {
    private var viewModel = HomeViewModel()
    private var storefront = StorefrontViewModel()
    private let scrollView = UIScrollView()
    private let storeStack = UIStackView()
    private let searchBar = UISearchBar()
    private let categoriesStack = UIStackView()
    private let productsStack = UIStackView()
    private let heroTitle = UILabel()
    private let heroSubtitle = UILabel()
    private let sectionTitle = UILabel()
    private let demoLabel = UILabel()
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
        view.backgroundColor = DesignTokens.Storefront.canvas

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

        let counterStack = UIStackView(arrangedSubviews: [titleLabel, counterLabel, buttonStack])
        counterStack.axis = .vertical
        counterStack.spacing = DesignTokens.Spacing.sm
        counterStack.isLayoutMarginsRelativeArrangement = true
        counterStack.directionalLayoutMargins = NSDirectionalEdgeInsets(top: DesignTokens.Spacing.xl, leading: 0, bottom: DesignTokens.Spacing.xl, trailing: 0)

        scrollView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.keyboardDismissMode = .onDrag
        view.addSubview(scrollView)
        storeStack.axis = .vertical
        storeStack.spacing = DesignTokens.Spacing.xl
        storeStack.translatesAutoresizingMaskIntoConstraints = false
        scrollView.addSubview(storeStack)
        configureStorefront()
        storeStack.addArrangedSubview(counterStack)
        let safeArea = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            scrollView.topAnchor.constraint(equalTo: safeArea.topAnchor),
            scrollView.bottomAnchor.constraint(equalTo: safeArea.bottomAnchor),
            scrollView.leadingAnchor.constraint(equalTo: safeArea.leadingAnchor),
            scrollView.trailingAnchor.constraint(equalTo: safeArea.trailingAnchor),
            storeStack.topAnchor.constraint(equalTo: scrollView.contentLayoutGuide.topAnchor, constant: DesignTokens.Spacing.lg),
            storeStack.bottomAnchor.constraint(equalTo: scrollView.contentLayoutGuide.bottomAnchor, constant: -DesignTokens.Spacing.xl),
            storeStack.leadingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.leadingAnchor, constant: DesignTokens.contentMargin),
            storeStack.trailingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.trailingAnchor, constant: -DesignTokens.contentMargin),
            storeStack.centerXAnchor.constraint(equalTo: scrollView.frameLayoutGuide.centerXAnchor),
            storeStack.widthAnchor.constraint(lessThanOrEqualToConstant: DesignTokens.contentMaxWidth),
            incrementButton.heightAnchor.constraint(greaterThanOrEqualToConstant: DesignTokens.minimumTapTarget),
            resetButton.heightAnchor.constraint(greaterThanOrEqualToConstant: DesignTokens.minimumTapTarget)
        ])
        let preferredWidth = storeStack.widthAnchor.constraint(equalTo: scrollView.frameLayoutGuide.widthAnchor, constant: -2 * DesignTokens.contentMargin)
        preferredWidth.priority = .defaultHigh
        preferredWidth.isActive = true
    }

    // 商城按搜索、主题推荐、分类和商品区排列，大字号时商品改为单列。
    private func configureStorefront() {
        searchBar.searchBarStyle = .minimal
        searchBar.delegate = self
        searchBar.accessibilityIdentifier = "shop.search"
        searchBar.searchTextField.font = .preferredFont(forTextStyle: .body)
        searchBar.searchTextField.adjustsFontForContentSizeCategory = true
        storeStack.addArrangedSubview(searchBar)
        styleLabel(heroTitle, style: .largeTitle)
        styleLabel(heroSubtitle, style: .body)
        heroTitle.textColor = DesignTokens.Storefront.accent
        heroSubtitle.textColor = DesignTokens.Colors.secondaryText
        let hero = UIStackView(arrangedSubviews: [heroTitle, heroSubtitle])
        hero.axis = .vertical
        hero.spacing = DesignTokens.Spacing.md
        hero.backgroundColor = DesignTokens.Storefront.artwork
        hero.layer.cornerRadius = DesignTokens.Radius.lg
        hero.isLayoutMarginsRelativeArrangement = true
        hero.directionalLayoutMargins = NSDirectionalEdgeInsets(top: DesignTokens.Spacing.xxl, leading: DesignTokens.Spacing.xl, bottom: DesignTokens.Spacing.xxl, trailing: DesignTokens.Spacing.xl)
        storeStack.addArrangedSubview(hero)
        categoriesStack.spacing = DesignTokens.Spacing.sm
        categoriesStack.distribution = .fillEqually
        storeStack.addArrangedSubview(categoriesStack)
        styleLabel(sectionTitle, style: .title2)
        storeStack.addArrangedSubview(sectionTitle)
        productsStack.axis = .vertical
        productsStack.spacing = DesignTokens.Spacing.lg
        storeStack.addArrangedSubview(productsStack)
        styleLabel(demoLabel, style: .footnote)
        demoLabel.textColor = DesignTokens.Colors.secondaryText
        storeStack.addArrangedSubview(demoLabel)
    }

    // 标题与正文均随系统字号缩放，并允许本地化文本换行。
    private func styleLabel(_ label: UILabel, style: UIFont.TextStyle) {
        label.font = .preferredFont(forTextStyle: style)
        label.adjustsFontForContentSizeCategory = true
        label.numberOfLines = 0
    }

    // 只更新商品区，搜索输入保持焦点，切换语言后重新匹配显示名称。
    private func renderStorefront() {
        searchBar.placeholder = LocalizationPolicy.localized("shop.search")
        heroTitle.text = LocalizationPolicy.localized("shop.hero")
        heroSubtitle.text = LocalizationPolicy.localized("shop.subtitle")
        sectionTitle.text = LocalizationPolicy.localized("shop.featured")
        demoLabel.text = LocalizationPolicy.localized("shop.demo")
        categoriesStack.axis = traitCollection.preferredContentSizeCategory.isAccessibilityCategory ? .vertical : .horizontal
        categoriesStack.arrangedSubviews.forEach { $0.removeFromSuperview() }
        for category in storefront.categories {
            let button = UIButton(type: .system)
            button.setTitle(LocalizationPolicy.localized("shop.category.\(category)"), for: .normal)
            button.titleLabel?.font = .preferredFont(forTextStyle: .subheadline)
            button.titleLabel?.adjustsFontForContentSizeCategory = true
            button.titleLabel?.numberOfLines = 0
            button.titleLabel?.textAlignment = .center
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: DesignTokens.minimumTapTarget).isActive = true
            button.layer.cornerRadius = DesignTokens.Radius.md
            button.backgroundColor = category == storefront.category ? DesignTokens.Storefront.artwork : DesignTokens.Colors.background
            button.tintColor = DesignTokens.Storefront.accent
            button.accessibilityIdentifier = "shop.category.\(category)"
            button.accessibilityTraits = category == storefront.category ? [.button, .selected] : [.button]
            button.addAction(UIAction { [weak self] _ in
                self?.storefront.category = category
                self?.renderStorefront()
            }, for: .touchUpInside)
            categoriesStack.addArrangedSubview(button)
        }
        productsStack.arrangedSubviews.forEach { $0.removeFromSuperview() }
        let products = storefront.filteredProducts(localize: LocalizationPolicy.localized)
        let columns = traitCollection.preferredContentSizeCategory.isAccessibilityCategory ? 1 : 2
        for offset in stride(from: 0, to: products.count, by: columns) {
            let row = UIStackView()
            row.spacing = DesignTokens.Spacing.lg
            row.distribution = .fillEqually
            for index in offset..<min(offset + columns, products.count) {
                row.addArrangedSubview(productCard(products[index]))
            }
            if row.arrangedSubviews.count < columns { row.addArrangedSubview(UIView()) }
            productsStack.addArrangedSubview(row)
        }
        if products.isEmpty {
            let empty = UILabel()
            styleLabel(empty, style: .body)
            empty.text = LocalizationPolicy.localized("shop.empty")
            empty.accessibilityIdentifier = "shop.empty"
            productsStack.addArrangedSubview(empty)
        }
    }

    // 商品整体可点击；VoiceOver 读取名称、价格并进入同一详情操作。
    private func productCard(_ product: StoreProduct) -> UIView {
        let button = UIButton(type: .custom)
        button.backgroundColor = DesignTokens.Colors.background
        button.layer.cornerRadius = DesignTokens.Radius.lg
        button.accessibilityIdentifier = "shop.product.\(product.id)"
        let icon = UIImageView(image: UIImage(systemName: product.symbol))
        icon.preferredSymbolConfiguration = UIImage.SymbolConfiguration(pointSize: DesignTokens.Storefront.artworkSize, weight: .light)
        icon.tintColor = DesignTokens.Storefront.accent
        icon.contentMode = .center
        icon.backgroundColor = DesignTokens.Storefront.artwork
        icon.layer.cornerRadius = DesignTokens.Radius.md
        icon.clipsToBounds = true
        icon.heightAnchor.constraint(equalToConstant: DesignTokens.Storefront.artworkHeight).isActive = true
        let name = UILabel()
        styleLabel(name, style: .headline)
        name.text = LocalizationPolicy.localized(product.titleKey)
        let price = UILabel()
        styleLabel(price, style: .subheadline)
        price.text = formattedPrice(product)
        price.textColor = DesignTokens.Storefront.accent
        let stack = UIStackView(arrangedSubviews: [icon, name, price])
        stack.axis = .vertical
        stack.spacing = DesignTokens.Spacing.md
        stack.isUserInteractionEnabled = false
        stack.translatesAutoresizingMaskIntoConstraints = false
        button.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: button.topAnchor, constant: DesignTokens.Spacing.md),
            stack.bottomAnchor.constraint(equalTo: button.bottomAnchor, constant: -DesignTokens.Spacing.lg),
            stack.leadingAnchor.constraint(equalTo: button.leadingAnchor, constant: DesignTokens.Spacing.md),
            stack.trailingAnchor.constraint(equalTo: button.trailingAnchor, constant: -DesignTokens.Spacing.md)
        ])
        button.accessibilityLabel = [name.text, price.text].compactMap { $0 }.joined(separator: ", ")
        button.addAction(UIAction { [weak self] _ in
            guard let self = self else { return }
            self.searchBar.resignFirstResponder()
            let alert = UIAlertController(title: LocalizationPolicy.localized(product.titleKey), message: self.formattedPrice(product) + "\n\n" + LocalizationPolicy.localized("shop.demo"), preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: LocalizationPolicy.localized("shop.close"), style: .default))
            self.present(alert, animated: true)
        }, for: .touchUpInside)
        return button
    }

    // 示例价格固定使用人民币，并按当前界面语言格式化。
    private func formattedPrice(_ product: StoreProduct) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CNY"
        formatter.locale = LocalizationPolicy.selectedLanguage.resourceCode.map { Locale(identifier: $0) } ?? .current
        return formatter.string(from: NSDecimalNumber(decimal: product.price)) ?? NSDecimalNumber(decimal: product.price).stringValue
    }

    func searchBar(_ searchBar: UISearchBar, textDidChange searchText: String) {
        storefront.query = searchText
        renderStorefront()
    }

    func searchBarSearchButtonClicked(_ searchBar: UISearchBar) {
        searchBar.resignFirstResponder()
    }

    override func traitCollectionDidChange(_ previousTraitCollection: UITraitCollection?) {
        super.traitCollectionDidChange(previousTraitCollection)
        if previousTraitCollection?.preferredContentSizeCategory != traitCollection.preferredContentSizeCategory {
            renderStorefront()
        }
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
        renderStorefront()
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
