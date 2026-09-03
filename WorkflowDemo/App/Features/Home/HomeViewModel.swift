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
