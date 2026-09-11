// Optional macOS PNG comparison helper. No third-party package or App dependency.
import AppKit
import CryptoKit
import ImageIO

struct SnapshotError: Error, CustomStringConvertible {
    let description: String
    init(_ message: String) { description = message }
}

struct Pixels {
    let width: Int
    let height: Int
    var rgba: [UInt8]
}

func decode(_ data: Data) throws -> Pixels {
    guard data.prefix(8) == Data([137, 80, 78, 71, 13, 10, 26, 10]),
          let source = CGImageSourceCreateWithData(data as CFData, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
          image.width > 0, image.height > 0, image.width <= 8192, image.height <= 8192 else {
        throw SnapshotError("Expected a valid PNG no larger than 8192 pixels per dimension")
    }
    var pixels = Pixels(width: image.width, height: image.height,
                        rgba: [UInt8](repeating: 0, count: image.width * image.height * 4))
    try pixels.rgba.withUnsafeMutableBytes { bytes in
        guard let space = CGColorSpace(name: CGColorSpace.sRGB),
              let context = CGContext(data: bytes.baseAddress, width: image.width, height: image.height,
                  bitsPerComponent: 8, bytesPerRow: image.width * 4, space: space,
                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue) else {
            throw SnapshotError("Cannot decode PNG to sRGB pixels")
        }
        context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
    }
    return pixels
}

func png(_ pixels: inout Pixels) throws -> Data {
    let width = pixels.width, height = pixels.height
    return try pixels.rgba.withUnsafeMutableBytes { bytes in
        guard let space = CGColorSpace(name: CGColorSpace.sRGB),
              let context = CGContext(data: bytes.baseAddress, width: width, height: height,
                  bitsPerComponent: 8, bytesPerRow: width * 4, space: space,
                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue),
              let image = context.makeImage(),
              let data = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]) else {
            throw SnapshotError("Cannot encode PNG diff")
        }
        return data
    }
}

func json(_ value: [String: Any]) throws -> Data {
    try JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
}

func readJSON(_ path: URL) throws -> [String: Any] {
    guard let object = try JSONSerialization.jsonObject(with: Data(contentsOf: path)) as? [String: Any] else {
        throw SnapshotError("Expected a JSON object: \(path.path)")
    }
    return object
}

func nonempty(_ value: Any?) -> Bool {
    guard let text = value as? String else { return false }
    return !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
}

func actualFact(_ value: Any?) -> Bool {
    guard let text = value as? String else { return false }
    let normalized = text.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ").lowercased()
    let unknown = Set(["unknown", "incomplete", "not_run", "not run", "n/a", "tbd", "未知", "待补充"])
    return !normalized.isEmpty && !unknown.contains(normalized) && !normalized.hasPrefix("replace_")
}

func integer(_ value: Any?) -> Int? {
    guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else { return nil }
    return value as? Int
}

func validateContext(_ context: [String: Any], _ pixels: Pixels) throws {
    for key in ["xcode", "simulator_runtime", "device_model", "locale", "interface_style",
                "content_size_category", "orientation", "scenario"] where !actualFact(context[key]) {
        throw SnapshotError("Capture context requires an actual value for \(key); unknown or placeholder values are not evidence")
    }
    if context.values.contains(where: { $0 is String && !actualFact($0) }) {
        throw SnapshotError("Replace unknown values and example placeholders with actual capture facts")
    }
    guard ["light", "dark"].contains(context["interface_style"] as? String ?? ""),
          ["portrait", "landscape"].contains(context["orientation"] as? String ?? ""),
          let width = context["viewport_width_points"] as? NSNumber,
          let height = context["viewport_height_points"] as? NSNumber,
          let scale = context["display_scale"] as? NSNumber,
          CFGetTypeID(width) != CFBooleanGetTypeID(), CFGetTypeID(height) != CFBooleanGetTypeID(),
          CFGetTypeID(scale) != CFBooleanGetTypeID(),
          width.doubleValue > 0, height.doubleValue > 0, scale.doubleValue > 0,
          width.doubleValue * scale.doubleValue == Double(pixels.width),
          height.doubleValue * scale.doubleValue == Double(pixels.height) else {
        throw SnapshotError("Capture context style, orientation or point dimensions/scale do not match PNG")
    }
}

func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

func exclusiveDirectory(_ directory: URL) throws {
    try FileManager.default.createDirectory(at: directory.deletingLastPathComponent(), withIntermediateDirectories: true)
    guard mkdir(directory.path, 0o700) == 0 else {
        throw SnapshotError("Directory must be new; existing evidence is never overwritten: \(directory.path)")
    }
}

func run() throws -> Int32 {
    let arguments = Array(CommandLine.arguments.dropFirst())
    guard let action = arguments.first, ["record", "compare"].contains(action), arguments.count % 2 == 1 else {
        throw SnapshotError("Usage: visual_snapshot.swift record|compare --image PNG --context JSON --baseline DIR "
            + "[record: --reviewed-by NAME --review-reference REF] [compare: --output NEW_DIR]")
    }
    var options = [String: String]()
    let allowed = Set(["--image", "--context", "--baseline"] + (action == "record"
        ? ["--reviewed-by", "--review-reference"] : ["--output"]))
    for index in stride(from: 1, to: arguments.count, by: 2) {
        let key = arguments[index], value = arguments[index + 1]
        guard allowed.contains(key), options[key] == nil, nonempty(value) else { throw SnapshotError("Invalid option: \(key)") }
        options[key] = value
    }
    guard Set(options.keys) == allowed else { throw SnapshotError("Missing required options for \(action)") }
    func path(_ key: String) -> URL { URL(fileURLWithPath: options[key]!) }
    let baseline = path("--baseline")
    let image = try Data(contentsOf: path("--image"))
    let current = try decode(image)
    let context = try readJSON(path("--context"))
    try validateContext(context, current)
    if action == "record" {
        guard actualFact(options["--reviewed-by"]), actualFact(options["--review-reference"]) else {
            throw SnapshotError("Baseline requires an actual reviewer and review reference")
        }
        let manifest: [String: Any] = ["schema_version": 1, "context": context,
            "image_sha256": digest(image), "width": current.width, "height": current.height,
            "reviewed_by": options["--reviewed-by"]!, "review_reference": options["--review-reference"]!,
            "recorded_at": ISO8601DateFormatter().string(from: Date())]
        let manifestData = try json(manifest)
        try exclusiveDirectory(baseline)
        try image.write(to: baseline.appendingPathComponent("image.png"), options: .atomic)
        try manifestData.write(to: baseline.appendingPathComponent("manifest.json"), options: .atomic)
        print("baseline recorded; review declaration saved; no comparison was performed")
        return 0
    }
    let output = path("--output")
    try exclusiveDirectory(output)
    var report: [String: Any] = ["result": "blocked", "context": context, "current_sha256": digest(image),
        "comparison": "exact sRGB RGBA pixels", "baseline": baseline.path]
    do {
        let manifest = try readJSON(baseline.appendingPathComponent("manifest.json"))
        let referenceData = try Data(contentsOf: baseline.appendingPathComponent("image.png"))
        guard integer(manifest["schema_version"]) == 1, actualFact(manifest["reviewed_by"]),
              actualFact(manifest["review_reference"]), manifest["image_sha256"] as? String == digest(referenceData),
              let recordedContext = manifest["context"] as? [String: Any] else {
            throw SnapshotError("Baseline is incomplete, changed or lacks a review declaration")
        }
        guard try json(recordedContext) == json(context) else { throw SnapshotError("Capture environment differs from reviewed baseline") }
        let reference = try decode(referenceData)
        guard reference.width == current.width, reference.height == current.height,
              integer(manifest["width"]) == reference.width, integer(manifest["height"]) == reference.height else {
            throw SnapshotError("Image dimensions differ from reviewed baseline")
        }
        var changed = 0
        var difference = current
        for offset in stride(from: 0, to: current.rgba.count, by: 4) {
            let different = (0..<4).contains { current.rgba[offset + $0] != reference.rgba[offset + $0] }
            if different { changed += 1 }
            difference.rgba[offset] = different ? 255 : current.rgba[offset] / 4
            difference.rgba[offset + 1] = different ? 0 : current.rgba[offset + 1] / 4
            difference.rgba[offset + 2] = different ? 255 : current.rgba[offset + 2] / 4
            difference.rgba[offset + 3] = 255
        }
        report["result"] = changed == 0 ? "passed" : "failed"
        report["changed_pixels"] = changed
        report["total_pixels"] = current.width * current.height
        report["baseline_sha256"] = digest(referenceData)
        try image.write(to: output.appendingPathComponent("current.png"), options: .atomic)
        if changed > 0 { try png(&difference).write(to: output.appendingPathComponent("diff.png"), options: .atomic) }
        try json(report).write(to: output.appendingPathComponent("report.json"), options: .atomic)
        print("visual comparison: \(changed == 0 ? "passed" : "failed"); changed pixels: \(changed); \(output.path)/report.json")
        return changed == 0 ? 0 : 1
    } catch {
        report["error"] = String(describing: error)
        try json(report).write(to: output.appendingPathComponent("report.json"), options: .atomic)
        throw error
    }
}

do { exit(try run()) } catch {
    FileHandle.standardError.write(Data("visual comparison blocked: \(error)\n".utf8))
    exit(2)
}
