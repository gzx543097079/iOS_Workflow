import UIKit

// 集中定义界面使用的尺寸、颜色和动效常量，避免业务页面散落魔法数字。
enum DesignTokens {
    // Spacing 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 32
    }

    // Radius 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
    }

    // ControlHeight 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum ControlHeight {
        static let sm: CGFloat = 32
        static let md: CGFloat = 44
        static let lg: CGFloat = 52
    }

    // IconSize 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum IconSize {
        static let sm: CGFloat = 16
        static let md: CGFloat = 24
        static let lg: CGFloat = 32
    }

    // BorderWidth 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum BorderWidth {
        static let hairline: CGFloat = 0.5
        static let regular: CGFloat = 1
    }

    // Opacity 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum Opacity {
        static let disabled: Double = 0.38
        static let secondary: Double = 0.68
        static let overlay: Double = 0.45
    }

    // AnimationDuration 中的值由工作流配置生成，修改视觉规范时应回到 Design Tokens 配置。
    enum AnimationDuration {
        static let quick: TimeInterval = 0.2
        static let normal: TimeInterval = 0.3
    }

    static let contentMargin: CGFloat = 16
    static let contentMaxWidth: CGFloat = 680
    static let minimumTapTarget: CGFloat = 44

    enum Typography {
        static let title: UIFont.TextStyle = UIFont.TextStyle.title2
        static let headline: UIFont.TextStyle = UIFont.TextStyle.headline
        static let body: UIFont.TextStyle = UIFont.TextStyle.body
        static let caption: UIFont.TextStyle = UIFont.TextStyle.caption1
    }

    enum Storefront {
        static let artworkHeight: CGFloat = 112
        static let artworkSize: CGFloat = 48
        static let accent = UIColor { $0.userInterfaceStyle == .dark ? .systemTeal : UIColor(red: 0.12, green: 0.35, blue: 0.28, alpha: 1) }
        static let canvas = UIColor { $0.userInterfaceStyle == .dark ? .systemBackground : UIColor(red: 0.97, green: 0.97, blue: 0.94, alpha: 1) }
        static let artwork = UIColor { $0.userInterfaceStyle == .dark ? .secondarySystemBackground : UIColor(red: 0.90, green: 0.93, blue: 0.88, alpha: 1) }
    }

    enum Colors {
        static let accent: UIColor = UIColor.systemBlue
        static let background: UIColor = UIColor.systemBackground
        static let secondaryBackground: UIColor = UIColor.secondarySystemBackground
        static let primaryText: UIColor = UIColor.label
        static let secondaryText: UIColor = UIColor.secondaryLabel
        static let separator: UIColor = UIColor.separator
        static let destructive: UIColor = UIColor.systemRed
    }
}
