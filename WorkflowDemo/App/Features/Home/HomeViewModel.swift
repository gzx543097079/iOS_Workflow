import Foundation

// 首页 Model 管理 Demo 计数状态，保持页面只负责展示和转发操作。
struct HomeViewModel {
    private(set) var count: Int

    let titleKey = "home.title"
    let counterKey = "counter.value"
    let incrementKey = "counter.increment"
    let resetKey = "counter.reset"

    init(count: Int = 0) {
        self.count = count
    }

    // 计数使用饱和递增，避免极端情况下发生整数溢出。
    mutating func increment() {
        guard count < Int.max else { return }
        count += 1
    }

    // 重置是幂等操作，便于页面和测试从任意计数恢复初始状态。
    mutating func reset() {
        count = 0
    }
}

// 本地样品只用于展示商城交互，价格不代表真实销售报价。
struct StoreProduct {
    let id: String
    let category: String
    let symbol: String
    let price: Decimal

    var titleKey: String { "shop.product.\(id)" }
}

// 搜索与分类共同筛选商品，界面语言由调用方提供以支持即时切换。
struct StorefrontViewModel {
    var category = "all"
    var query = ""
    let categories = ["all", "digital", "living"]
    let products = [
        StoreProduct(id: "headphones", category: "digital", symbol: "headphones", price: 299),
        StoreProduct(id: "lamp", category: "living", symbol: "lightbulb", price: 129),
        StoreProduct(id: "speaker", category: "digital", symbol: "hifispeaker", price: 199),
        StoreProduct(id: "mug", category: "living", symbol: "cup.and.saucer", price: 59)
    ]

    // 组合条件筛选，空白搜索等同于显示当前分类的全部商品。
    func filteredProducts(localize: (String) -> String) -> [StoreProduct] {
        let term = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return products.filter {
            (category == "all" || $0.category == category) &&
                (term.isEmpty || localize($0.titleKey).localizedCaseInsensitiveContains(term))
        }
    }
}
