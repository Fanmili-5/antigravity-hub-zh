import AppKit
import CoreImage
import Foundation
import ImageIO
import UniformTypeIdentifiers
import Vision

private let tile = 512

struct PetManifest: Codable {
    let version: Int
    let name: String
    let layout: String

    var valid: Bool {
        version == 1 && !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
            name.count <= 48 && name.rangeOfCharacter(from: .controlCharacters) == nil &&
            ["portrait", "poses"].contains(layout)
    }
}

enum PetAssetError: LocalizedError {
    case message(String)

    var errorDescription: String? {
        switch self { case .message(let detail): return detail }
    }
}

struct PetAssets {
    let name: String
    let frames: [NSImage]
    var animatedPoses: Bool { frames.count == 4 }

    func image(for mood: Mood) -> NSImage {
        guard animatedPoses else { return frames[0] }
        switch mood {
        case .idle: return frames[0]
        case .thinking: return frames[1]
        case .done: return frames[2]
        case .error: return frames[3]
        }
    }

    static func active() -> PetAssets? {
        let root = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Antigravity Hub Tools")
        let pointer = root.appendingPathComponent("active-pet.json")
        if let data = try? Data(contentsOf: pointer), data.count <= 256,
           let active = try? JSONDecoder().decode([String: String].self, from: data),
           let id = active["id"], id.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
           let pet = try? load(root.appendingPathComponent("Pets").appendingPathComponent(id)) {
            return pet
        }
        return Bundle.main.resourceURL.flatMap { try? load($0.appendingPathComponent("DefaultPet")) }
    }

    static func load(_ directory: URL) throws -> PetAssets {
        let config = try Data(contentsOf: directory.appendingPathComponent("pet.json"))
        guard config.count <= 4096 else { throw PetAssetError.message("桌宠清单过大。") }
        let manifest = try JSONDecoder().decode(PetManifest.self, from: config)
        guard manifest.valid else { throw PetAssetError.message("桌宠清单名称或图集格式无效。") }
        let file = directory.appendingPathComponent("atlas.png")
        let expected = manifest.layout == "poses" ? tile * 2 : tile
        guard let input = CGImageSourceCreateWithURL(file as CFURL, nil),
              CGImageSourceGetType(input) as String? == UTType.png.identifier,
              let props = CGImageSourceCopyPropertiesAtIndex(input, 0, nil) as? [CFString: Any],
              props[kCGImagePropertyPixelWidth] as? Int == expected,
              props[kCGImagePropertyPixelHeight] as? Int == expected,
              let atlas = CGImageSourceCreateImageAtIndex(input, 0, nil) else {
            throw PetAssetError.message("图集应为 \(expected)×\(expected) 的 PNG。")
        }
        let images = try split(atlas, count: manifest.layout == "poses" ? 4 : 1)
        guard images.allSatisfy({ bounds($0, threshold: 20) != nil }) else {
            throw PetAssetError.message("至少有一个状态缺少可见角色。")
        }
        return PetAssets(name: manifest.name, frames: images.map {
            NSImage(cgImage: $0, size: NSSize(width: tile, height: tile))
        })
    }

    static func prepare(input: URL, output: URL, manifest: PetManifest, keepBackground: Bool) throws {
        guard manifest.valid else { throw PetAssetError.message("桌宠名称或图集格式无效。") }
        let values = try input.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
        guard values.isRegularFile == true, let bytes = values.fileSize, bytes <= 24 * 1024 * 1024,
              let source = CGImageSourceCreateWithURL(input as CFURL, nil),
              let type = CGImageSourceGetType(source) as String?,
              [UTType.png.identifier, UTType.jpeg.identifier, UTType(filenameExtension: "webp")?.identifier]
                .compactMap({ $0 }).contains(type),
              CGImageSourceGetCount(source) == 1,
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceThumbnailMaxPixelSize: 2048,
                kCGImageSourceCreateThumbnailWithTransform: true,
              ] as CFDictionary) else {
            throw PetAssetError.message("请选择 24 MiB 以内的静态 PNG、JPEG 或 WebP。")
        }
        let isSheet = manifest.layout == "poses"
        if isSheet {
            guard abs(image.width - image.height) <= 4, image.width >= 256 else {
                throw PetAssetError.message("四姿势图集需为正方形，按 2×2 排列。")
            }
        }
        let frames = try split(image, count: isSheet ? 4 : 1).map { raw in
            if silhouette(raw) { return raw }
            if isSheet {
                throw PetAssetError.message("每个图格都需要透明留白，避免姿势挤到其他格。")
            }
            return keepBackground ? raw : try cutout(raw)
        }
        let cropped = try frames.map { frame -> CGImage in
            guard let rect = bounds(frame, threshold: 20), rect.width >= 16, rect.height >= 16,
                  let subject = frame.cropping(to: rect) else {
                throw PetAssetError.message("图中没有足够大的角色，请换一张主体清晰的图。")
            }
            return subject
        }
        let side = isSheet ? 2 : 1
        let size = tile * side
        guard let canvas = bitmap(width: size, height: size) else {
            throw PetAssetError.message("无法创建桌宠图集。")
        }
        canvas.interpolationQuality = .high
        for (index, subject) in cropped.enumerated() {
            let scale = min(400.0 / Double(subject.width), 406.0 / Double(subject.height))
            let width = Double(subject.width) * scale
            let height = Double(subject.height) * scale
            let x = Double(tile * (index % side)) + (Double(tile) - width) / 2
            let y = Double(tile * (side - 1 - index / side) + 42)
            canvas.draw(subject, in: CGRect(x: x, y: y, width: width, height: height))
        }
        let atlas = output.appendingPathComponent("atlas.png")
        guard let finalized = canvas.makeImage(),
              let encoder = CGImageDestinationCreateWithURL(atlas as CFURL, UTType.png.identifier as CFString, 1, nil) else {
            throw PetAssetError.message("无法写入桌宠图集。")
        }
        CGImageDestinationAddImage(encoder, finalized, nil)
        guard CGImageDestinationFinalize(encoder) else {
            throw PetAssetError.message("无法保存桌宠 PNG。")
        }
        let json = JSONEncoder()
        json.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        try json.encode(manifest).write(to: output.appendingPathComponent("pet.json"), options: .atomic)
        _ = try load(output)
    }

    private static func split(_ image: CGImage, count: Int) throws -> [CGImage] {
        if count == 1 { return [image] }
        let width = image.width / 2
        let height = image.height / 2
        return try (0..<4).map { index in
            guard let frame = image.cropping(to: CGRect(x: (index % 2) * width, y: (index / 2) * height,
                                                        width: width, height: height)) else {
                throw PetAssetError.message("无法裁切第 \(index + 1) 格。")
            }
            return frame
        }
    }

    private static func bitmap(width: Int, height: Int) -> CGContext? {
        CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4,
                  space: CGColorSpace(name: CGColorSpace.sRGB)!,
                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
    }

    private static func bounds(_ image: CGImage, threshold: UInt8) -> CGRect? {
        let (width, height) = (image.width, image.height)
        guard let context = bitmap(width: width, height: height),
              let base = context.data?.assumingMemoryBound(to: UInt8.self) else { return nil }
        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        var (left, right, top, bottom) = (width, -1, height, -1)
        for y in 0..<height {
            let row = base.advanced(by: y * context.bytesPerRow)
            for x in 0..<width where row[x * 4 + 3] >= threshold {
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)
            }
        }
        guard left <= right, top <= bottom else { return nil }
        return CGRect(x: left, y: top, width: right - left + 1, height: bottom - top + 1)
    }

    private static func silhouette(_ image: CGImage) -> Bool {
        guard let rect = bounds(image, threshold: 20) else { return true }
        // A cutout leaves transparent margin along some edge. Opaque images need Vision.
        return rect.width < Double(image.width) || rect.height < Double(image.height)
    }

    private static func cutout(_ image: CGImage) throws -> CGImage {
        guard #available(macOS 14.0, *) else {
            throw PetAssetError.message("自动抠图需要 macOS 14 以上，也可直接导入透明 PNG。")
        }
        let request = VNGenerateForegroundInstanceMaskRequest()
        let handler = VNImageRequestHandler(cgImage: image)
        try handler.perform([request])
        guard let observation = request.results?.first, !observation.allInstances.isEmpty else {
            throw PetAssetError.message("未检测到前景。请选择主体清晰的图片或透明 PNG。")
        }
        let mask = try observation.generateScaledMaskForImage(forInstances: observation.allInstances, from: handler)
        let input = CIImage(cgImage: image)
        let filtered = input.applyingFilter("CIBlendWithMask", parameters: [
            kCIInputBackgroundImageKey: CIImage.empty().cropped(to: input.extent),
            kCIInputMaskImageKey: CIImage(cvPixelBuffer: mask),
        ])
        guard let result = CIContext().createCGImage(filtered, from: input.extent),
              silhouette(result) else {
            throw PetAssetError.message("未得到透明边缘。请选择另一张图片或透明 PNG。")
        }
        return result
    }
}

func runAssetCommand(_ args: [String]) -> Bool {
    guard let command = args.first,
          ["--prepare-pet", "--validate-pet", "--validate-wallpaper"].contains(command) else { return false }
    do {
        if command == "--validate-wallpaper", args.count == 2 {
            let url = URL(fileURLWithPath: args[1])
            guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                  CGImageSourceGetType(source) as String? == UTType.jpeg.identifier,
                  CGImageSourceGetCount(source) == 1,
                  let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
                  let width = properties[kCGImagePropertyPixelWidth] as? Int,
                  let height = properties[kCGImagePropertyPixelHeight] as? Int,
                  (1...2560).contains(width), (1...2560).contains(height),
                  let decoded = CGImageSourceCreateImageAtIndex(source, 0, nil), decoded.width == width else {
                throw PetAssetError.message("壁纸需为 2560 px 以内、可解码的静态 JPEG。")
            }
        } else if command == "--validate-pet", args.count == 2 {
            let pet = try PetAssets.load(URL(fileURLWithPath: args[1], isDirectory: true))
            print(pet.animatedPoses ? "四姿势图集" : "单张角色图")
        } else if command == "--prepare-pet", args.count == 6 {
            try PetAssets.prepare(
                input: URL(fileURLWithPath: args[1]), output: URL(fileURLWithPath: args[2], isDirectory: true),
                manifest: PetManifest(version: 1, name: args[3], layout: args[4]),
                keepBackground: args[5] == "keep"
            )
        } else {
            throw PetAssetError.message("桌宠图集参数不完整。")
        }
    } catch {
        FileHandle.standardError.write(Data((error.localizedDescription + "\n").utf8))
        exit(2)
    }
    return true
}
