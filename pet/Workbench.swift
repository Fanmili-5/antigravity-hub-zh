import AppKit
import SwiftUI
import UniformTypeIdentifiers

extension Notification.Name {
    static let orbitAppearanceChanged = Notification.Name("orbitAppearanceChanged")
}

private struct PackEntry: Decodable, Identifiable {
    struct Skin: Decodable {
        let name: String
        let blur: Int
        let veil: Int
        let tint: String

        var accent: Color {
            guard let rgb = UInt32(tint.dropFirst(), radix: 16) else { return .accentColor }
            return Color(red: Double((rgb >> 16) & 255) / 255,
                         green: Double((rgb >> 8) & 255) / 255,
                         blue: Double(rgb & 255) / 255)
        }
    }

    let id: String
    let name: String
    let skin: Skin
    let petPath: String
    let wallpaperPath: String?
}

private struct PackLibrary: Decodable {
    let packs: [PackEntry]
    let active: String?
    let skin: String?
}

struct Driver: Decodable {
    let python: String
    let checkout: String

    static func load() -> Self? {
        guard let file = Bundle.main.url(forResource: "WorkbenchDriver", withExtension: "json"),
              let data = try? Data(contentsOf: file) else { return nil }
        return try? JSONDecoder().decode(Self.self, from: data)
    }
}

private enum CommandError: LocalizedError {
    case failed(String)
    var errorDescription: String? {
        switch self { case .failed(let message): return message }
    }
}

private final class WorkbenchRuntime {
    static let shared = Result { try WorkbenchRuntime() }
    let directory: URL
    private let temporary: URL

    private init() throws {
        guard let resource = Bundle.main.resourceURL else {
            throw CommandError.failed("工作台资源不完整，请重新构建。")
        }
        let files = FileManager.default
        temporary = files.temporaryDirectory.appendingPathComponent("agy-orbit-\(UUID().uuidString)", isDirectory: true)
        directory = temporary.appendingPathComponent("Workbench", isDirectory: true)
        try files.createDirectory(at: temporary, withIntermediateDirectories: false,
                                  attributes: [.posixPermissions: 0o700])
        do {
            try files.copyItem(at: resource.appendingPathComponent("Workbench", isDirectory: true), to: directory)
        } catch {
            try? files.removeItem(at: temporary)
            throw error
        }
    }

    deinit { try? FileManager.default.removeItem(at: temporary) }
}

private final class PackStore: NSObject, ObservableObject, NSOpenSavePanelDelegate {
    @Published private(set) var library = PackLibrary(packs: [], active: nil, skin: nil)
    @Published var selected: String? {
        didSet {
            guard oldValue != selected else { return }
            previewMood = .idle
            loadArt()
        }
    }
    @Published private(set) var wallpaper: NSImage?
    @Published private(set) var pet: PetAssets?
    @Published var previewMood = Mood.idle
    @Published private(set) var busy = false
    @Published private(set) var message = ""
    @Published private(set) var failed = false
    private let driver = Driver.load()
    private var showingPanel = false
    private var refreshQueued = false

    var entry: PackEntry? { library.packs.first { $0.id == selected } }

    func refresh(preserveMessage: Bool = true) {
        if busy || showingPanel {
            refreshQueued = true
            return
        }
        perform(["list", "--json"], preserveMessage: preserveMessage) { [weak self] data in
            try self?.receive(data, prefer: nil)
        }
    }

    private func receive(_ data: Data, prefer: String?) throws {
        library = try JSONDecoder().decode(PackLibrary.self, from: data)
        let choices = [prefer, selected, library.active].compactMap { $0 }
        let next = choices.first(where: { candidate in library.packs.contains { $0.id == candidate } })
            ?? library.packs.first?.id
        if selected == next {
            loadArt()
        } else {
            selected = next
        }
    }

    private func loadArt() {
        wallpaper = entry?.wallpaperPath.flatMap { NSImage(contentsOfFile: $0) }
        pet = entry.flatMap { try? PetAssets.load(URL(fileURLWithPath: $0.petPath, isDirectory: true)) }
    }

    func apply() {
        guard let entry else { return }
        perform(["apply", entry.id], refreshLibrary: true) { [weak self] _ in
            self?.message = "已应用「\(entry.name)」"
        }
    }

    func restore() {
        perform(["restore"], refreshLibrary: true) { [weak self] _ in
            self?.message = "已恢复切换前的外观"
        }
    }

    func importFile() {
        let picker = NSOpenPanel()
        picker.title = "导入外观套装"
        picker.prompt = "导入"
        picker.allowedContentTypes = [.zip]
        picker.canChooseDirectories = false
        present(picker) { [weak self] file in
            self?.perform(["import", file.path], refreshLibrary: true, preferCommandOutput: true) { [weak self] _ in
                self?.message = "已导入。现在可以预览并应用。"
            }
        }
    }

    func exportFile(current: Bool) {
        guard let reference = current ? "current" : entry?.id else { return }
        let panel = NSSavePanel()
        panel.title = current ? "导出当前外观" : "导出选中的套装"
        panel.prompt = "导出"
        panel.allowedContentTypes = [.zip]
        panel.delegate = self
        let name = current ? "我的反重力外观" : (entry?.name ?? "外观套装")
        panel.nameFieldStringValue = name.replacingOccurrences(of: "/", with: "／")
            .replacingOccurrences(of: ":", with: "：") + ".zip"
        present(panel) { [weak self] file in
            guard let self else { return }
            do {
                let staging = try WorkbenchRuntime.shared.get().directory
                    .appendingPathComponent(UUID().uuidString + ".zip")
                var args = ["export", reference, staging.path]
                if current { args.append("--name=\(file.deletingPathExtension().lastPathComponent)") }
                self.perform(args, cleanup: { try? FileManager.default.removeItem(at: staging) }) { [weak self] _ in
                    try FileManager.default.moveItem(at: staging, to: file)
                    self?.message = "已导出 \(file.lastPathComponent)"
                }
            } catch {
                self.fail(error)
            }
        }
    }

    func panel(_ sender: Any, validate url: URL) throws {
        if FileManager.default.fileExists(atPath: url.path) {
            throw CommandError.failed("已有同名文件，请为套装选择新的文件名。")
        }
    }

    func chooseWorkspace(enable: Bool) {
        let picker = NSOpenPanel()
        picker.title = enable ? "选择启用联动的工作区" : "选择停用联动的工作区"
        picker.prompt = enable ? "启用" : "停用"
        picker.canChooseFiles = false
        picker.canChooseDirectories = true
        present(picker) { [weak self] directory in
            self?.perform([enable ? "enable" : "disable", directory.path], script: "pet.py") { [weak self] _ in
                let name = directory.lastPathComponent
                self?.message = enable ? "已为「\(name)」写入 Hook。如 Hub 提示审查，请在那里确认。"
                    : "「\(name)」的联动已停用。"
            }
        }
    }

    private func present(_ panel: NSSavePanel, selection: @escaping (URL) -> Void) {
        guard !busy, !showingPanel,
              let workbench = NSApp.windows.first(where: { $0.identifier?.rawValue == "OrbitWorkbench" }) else { return }
        showingPanel = true
        panel.beginSheetModal(for: workbench) { [weak self] result in
            guard let self else { return }
            self.showingPanel = false
            if result == .OK, let url = panel.url { selection(url) }
            self.refreshIfQueued()
        }
    }

    private func refreshIfQueued() {
        guard refreshQueued, !busy, !showingPanel else { return }
        refreshQueued = false
        refresh()
    }

    private func fail(_ error: Error) {
        failed = true
        message = error.localizedDescription
    }

    private func perform(_ args: [String], script: String = "pack.py", refreshLibrary: Bool = false,
                         preferCommandOutput: Bool = false, preserveMessage: Bool = false,
                         cleanup: (() -> Void)? = nil,
                         finish: @escaping (Data) throws -> Void) {
        guard !busy else { cleanup?(); return }
        busy = true
        if !preserveMessage {
            failed = false
            message = ""
        }
        let driver = self.driver
        DispatchQueue.global(qos: .userInitiated).async {
            let result = Result {
                guard let driver else {
                    throw CommandError.failed("缺少本机工具入口，请从源码目录重新运行 python3 pack.py workbench。")
                }
                let result = try WorkbenchCommand.call(driver, args, script: script)
                let library = try refreshLibrary ? WorkbenchCommand.call(driver, ["list", "--json"], script: "pack.py") : nil
                return (result, library)
            }
            DispatchQueue.main.async { [weak self] in
                defer { cleanup?() }
                guard let self else { return }
                defer {
                    self.busy = false
                    self.refreshIfQueued()
                }
                do {
                    let (output, library) = try result.get()
                    if let library {
                        let preferred = preferCommandOutput
                            ? String(decoding: output, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
                            : nil
                        try self.receive(library, prefer: preferred)
                    }
                    try finish(output)
                } catch {
                    self.fail(error)
                }
            }
        }
    }

}

enum WorkbenchCommand {
    static func call(_ driver: Driver, _ args: [String], script name: String) throws -> Data {
        guard let executable = Bundle.main.executableURL else {
            throw CommandError.failed("工作台资源不完整，请重新构建。")
        }
        let base = try WorkbenchRuntime.shared.get().directory
        let script = base.appendingPathComponent(name)
        guard FileManager.default.isReadableFile(atPath: script.path),
              FileManager.default.isExecutableFile(atPath: driver.python) else {
            throw CommandError.failed("找不到本机工具脚本或 Python，请重新构建工作台。")
        }
        let task = Process()
        task.currentDirectoryURL = base
        task.executableURL = URL(fileURLWithPath: driver.python)
        task.arguments = ["-B", script.path] + args
        var environment = ProcessInfo.processInfo.environment
        environment["AGY_ORBIT_ASSET_BINARY"] = executable.path
        environment["AGY_ORBIT_HOOK_SCRIPT"] = URL(fileURLWithPath: driver.checkout)
            .appendingPathComponent("pet.py").path
        task.environment = environment
        let files = FileManager.default
        let log = files.temporaryDirectory.appendingPathComponent("agy-workbench-\(UUID().uuidString).log")
        guard files.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
            throw CommandError.failed("无法创建本地命令输出。")
        }
        defer { try? files.removeItem(at: log) }
        let output = try FileHandle(forWritingTo: log)
        defer { try? output.close() }
        task.standardOutput = output
        task.standardError = output
        try task.run()
        let timeout = DispatchWorkItem { if task.isRunning { task.terminate() } }
        DispatchQueue.global().asyncAfter(deadline: .now() + 20, execute: timeout)
        task.waitUntilExit()
        timeout.cancel()
        let result = try Data(contentsOf: log)
        guard task.terminationStatus == 0 else {
            let text = String(decoding: result, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
            throw CommandError.failed(text.isEmpty ? "命令退出，状态 \(task.terminationStatus)" : String(text.suffix(900)))
        }
        return result
    }
}

struct WorkbenchView: View {
    @ObservedObject var activity: LiveActivity
    var openHub: () -> Void
    @StateObject private var store = PackStore()
    @State private var section = "外观套装"

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("反重力工作台")
                        .font(.system(size: 28, weight: .semibold))
                    Text(store.library.skin.map { "本地皮肤  ·  \($0)" } ?? "本地皮肤  ·  默认外观")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Picker("工作台分区", selection: $section) {
                    Text("外观套装").tag("外观套装")
                    Text("会话活动").tag("会话活动")
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .frame(width: 216)
                Button(action: openHub) { Label("打开 Hub", systemImage: "arrow.up.right").labelStyle(.titleAndIcon) }
            }
            .padding(.horizontal, 26)
            .padding(.vertical, 18)
            Divider()
            if section == "会话活动" {
                activityPane
            } else {
                packsPane
            }
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .frame(minWidth: 780, minHeight: 555)
        .onAppear { store.refresh() }
        .onReceive(NotificationCenter.default.publisher(for: .orbitAppearanceChanged)) { _ in store.refresh() }
        .onReceive(NotificationCenter.default.publisher(for: NSWindow.didBecomeKeyNotification)) { event in
            if (event.object as? NSWindow)?.identifier?.rawValue == "OrbitWorkbench" { store.refresh() }
        }
    }

    private var packsPane: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("套装库").font(.headline)
                    Spacer()
                    Button { store.refresh(preserveMessage: false) } label: { Image(systemName: "arrow.clockwise") }
                        .buttonStyle(.borderless).help("刷新套装库").accessibilityLabel("刷新套装库")
                        .disabled(store.busy)
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(store.library.packs) { pack in
                            Button {
                                store.selected = pack.id
                            } label: {
                                HStack(alignment: .top, spacing: 10) {
                                    Image(systemName: pack.wallpaperPath == nil ? "paintpalette" : "photo")
                                        .foregroundStyle(Color.accentColor)
                                        .frame(width: 17)
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(pack.name).font(.system(size: 13, weight: .medium)).lineLimit(2)
                                        Text(store.library.active == pack.id ? "使用中" : (pack.id == "fjord" ? "内置" : "已导入"))
                                            .font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer(minLength: 0)
                                    if store.library.active == pack.id {
                                        Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.accentColor)
                                    }
                                }
                                .padding(.vertical, 10)
                                .padding(.horizontal, 9)
                                .background(store.selected == pack.id ? Color.accentColor.opacity(0.13) : .clear,
                                            in: RoundedRectangle(cornerRadius: 9))
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .accessibilityAddTraits(store.selected == pack.id ? .isSelected : [])
                        }
                    }
                }
                Button(action: store.importFile) { Label("导入套装…", systemImage: "square.and.arrow.down") }
                    .disabled(store.busy)
            }
            .padding(18)
            .frame(width: 220)
            .background(.background.opacity(0.38))
            Divider()
            VStack(alignment: .leading, spacing: 13) {
                if let entry = store.entry {
                    HStack(alignment: .center) {
                        Text(entry.name).font(.title2.weight(.semibold)).lineLimit(2)
                        Spacer()
                        if store.pet?.animatedPoses == true {
                            Picker("桌宠姿势", selection: $store.previewMood) {
                                Text(Mood.idle.label).tag(Mood.idle)
                                Text(Mood.thinking.label).tag(Mood.thinking)
                                Text(Mood.done.label).tag(Mood.done)
                                Text(Mood.error.label).tag(Mood.error)
                            }
                            .fixedSize()
                        }
                    }
                    stage(entry)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    Text("壁纸与磨砂在安装工具箱补丁后的 Hub 聊天页生效。")
                        .font(.callout).foregroundStyle(.secondary)
                    HStack(spacing: 9) {
                        Button(action: store.apply) {
                            Label(store.library.active == entry.id ? "重新应用" : "应用套装", systemImage: "checkmark")
                        }
                        .buttonStyle(.borderedProminent).disabled(store.busy)
                        Button("导出套装…") { store.exportFile(current: false) }.disabled(store.busy)
                        Menu("更多") {
                            Button("导出当前组合…") { store.exportFile(current: true) }
                                .disabled(store.library.skin == nil)
                            Button("撤销套装切换", action: store.restore)
                                .disabled(store.library.active == nil)
                        }
                        .fixedSize().disabled(store.busy)
                    }
                } else {
                    Spacer()
                    Text(store.busy ? "正在读取套装库…" : "套装库暂不可用")
                        .foregroundStyle(.secondary).frame(maxWidth: .infinity)
                    Spacer()
                }
                HStack {
                    if store.busy { ProgressView().controlSize(.small) }
                    Text(store.message)
                        .font(.callout)
                        .foregroundStyle(store.failed ? Color.red : Color.secondary)
                        .lineLimit(3)
                }
                .frame(minHeight: 17, alignment: .leading)
                .accessibilityLabel(store.message.isEmpty && store.busy ? "正在处理" : store.message)
            }
            .padding(19)
        }
    }

    private func stage(_ pack: PackEntry) -> some View {
        GeometryReader { box in
            ZStack(alignment: .bottomLeading) {
                LinearGradient(colors: [pack.skin.accent, Color(nsColor: .windowBackgroundColor)],
                               startPoint: .topLeading, endPoint: .bottomTrailing)
                if let wallpaper = store.wallpaper {
                    Image(nsImage: wallpaper)
                        .resizable().scaledToFill()
                        .frame(width: box.size.width, height: box.size.height).clipped()
                        .accessibilityHidden(true)
                }
                Color(nsColor: .windowBackgroundColor).opacity(Double(pack.skin.veil) / 100)
                HStack(alignment: .bottom, spacing: 8) {
                    VStack(alignment: .leading, spacing: 7) {
                        Text(pack.skin.name).font(.headline)
                        if let pet = store.pet { Text(pet.name).font(.subheadline) }
                        Text("遮罩 \(pack.skin.veil)%  ·  磨砂 \(pack.skin.blur) px")
                            .font(.caption).monospacedDigit()
                    }
                    .foregroundStyle(.primary)
                    .padding(13)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(pack.skin.accent.opacity(0.55)))
                    Spacer(minLength: 0)
                    if let pet = store.pet {
                        Image(nsImage: pet.image(for: store.previewMood))
                            .resizable().scaledToFit()
                            .frame(width: min(box.size.width * 0.43, 238), height: min(box.size.height * 0.73, 238))
                            .shadow(color: .black.opacity(0.22), radius: 11, x: 0, y: 9)
                            .accessibilityLabel("\(pet.name)，\(store.previewMood.label)")
                    }
                }
                .padding(18)
            }
            .clipShape(RoundedRectangle(cornerRadius: 16))
        }
        .frame(minHeight: 275)
    }

    private var activityPane: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("会话活动").font(.title2.weight(.semibold))
                Spacer()
                Text("\(activity.running) 个运行中   ·   \(activity.records.count - activity.running) 个已结束")
                    .monospacedDigit().font(.subheadline).foregroundStyle(.secondary)
            }
            HStack {
                Button("启用工作区…") { store.chooseWorkspace(enable: true) }
                Button("停用工作区…") { store.chooseWorkspace(enable: false) }
                if store.busy { ProgressView().controlSize(.small) }
                Text(store.message).foregroundStyle(store.failed ? Color.red : Color.secondary)
                    .font(.callout).lineLimit(2)
            }
            .disabled(store.busy)
            Divider()
            if activity.groups.isEmpty {
                VStack(spacing: 9) {
                    Image(systemName: "waveform.path").font(.system(size: 29)).foregroundStyle(.secondary)
                    Text("还没有收到会话事件").font(.headline)
                    Text("启用一个工作区后，在 Hub 内从该工作区开始会话。")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        ForEach(activity.groups) { group in
                            VStack(alignment: .leading, spacing: 8) {
                                Label(group.label, systemImage: "folder")
                                    .font(.headline)
                                ForEach(group.sessions) { session in
                                    if session.ended == nil {
                                        TimelineView(.periodic(from: session.started, by: 1)) { context in
                                            activityRow(session, now: context.date)
                                        }
                                    } else {
                                        activityRow(session, now: session.updated)
                                    }
                                }
                            }
                            .padding(12)
                            .background(.background.opacity(0.60), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .padding(22)
    }

    private func activityRow(_ session: ActivitySession, now: Date) -> some View {
        let seconds = session.duration(at: now)
        let duration = seconds < 60 ? "\(seconds) 秒" : "\(seconds / 60) 分 \(seconds % 60) 秒"
        return HStack(spacing: 12) {
            Circle().fill(Color(nsColor: session.mood.tint)).frame(width: 8, height: 8).accessibilityHidden(true)
            Text("会话 \(session.id.prefix(6))").font(.system(.body, design: .monospaced))
            Spacer()
            Text(session.mood.label).frame(minWidth: 72, alignment: .leading)
            Text(duration).monospacedDigit().frame(minWidth: 80, alignment: .trailing)
            Text(session.updated, style: .time).monospacedDigit().foregroundStyle(.secondary)
                .frame(minWidth: 75, alignment: .trailing)
        }
        .padding(.vertical, 6)
        .padding(.horizontal, 5)
        .accessibilityElement(children: .combine)
    }
}

func makeWorkbench(activity: LiveActivity, openHub: @escaping () -> Void) -> NSWindow {
    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 960, height: 650),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
    window.title = "反重力工作台"
    window.identifier = NSUserInterfaceItemIdentifier("OrbitWorkbench")
    window.isReleasedWhenClosed = false
    window.minSize = NSSize(width: 780, height: 580)
    window.contentView = NSHostingView(rootView: WorkbenchView(activity: activity, openHub: openHub))
    window.center()
    return window
}
