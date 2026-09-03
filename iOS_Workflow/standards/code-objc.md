# Objective-C 规范

- 类使用项目规定的 2–3 位前缀；方法和属性使用 lower camel case，分类文件使用 `ClassName+Purpose`。
- 启用 nullability 和轻量泛型；公共头文件只暴露必要 API，私有声明放入 class extension。
- 属性准确使用 `strong`、`copy`、`weak`、`assign`；Block 通常 `copy`，delegate 通常 `weak`。
- 新异步 API 明确回调线程和错误语义；不无理由扩大 Objective-C 桥接面。
- 避免新增宏式常量，优先 `static const` 或类型安全封装。
