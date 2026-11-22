import AppKit
import Darwin

enum Mood: String {
    case idle, thinking, done, error

    var label: String {
        switch self {
        case .idle: return "待机"
        case .thinking: return "正在思考"
        case .done: return "已完成"
        case .error: return "需要查看"
        }
    }

    var tint: NSColor {
        switch self {
        case .idle: return NSColor(srgbRed: 0.52, green: 0.82, blue: 0.70, alpha: 1)
        case .thinking: return NSColor(srgbRed: 0.65, green: 0.70, blue: 1, alpha: 1)
        case .done: return NSColor(srgbRed: 1, green: 0.79, blue: 0.46, alpha: 1)
        case .error: return NSColor(srgbRed: 1, green: 0.60, blue: 0.58, alpha: 1)
        }
    }
}

final class OrbitView: NSView {
    var onActivate: (() -> Void)?
    private var dragStart: NSPoint?
    private var windowStart = NSPoint.zero
    private var dragging = false

    var assets: PetAssets? {
        didSet { updateAccessibility(); needsDisplay = true }
    }

    private var moodSince = ProcessInfo.processInfo.systemUptime
    var mood = Mood.idle {
        didSet {
            if mood != oldValue {
                moodSince = ProcessInfo.processInfo.systemUptime
                updateAccessibility()
                NSAccessibility.post(element: self, notification: .valueChanged)
            }
            needsDisplay = true
        }
    }

    var name: String { assets?.name ?? "Orbit Pet" }
    override var mouseDownCanMoveWindow: Bool { false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    override func mouseDown(with event: NSEvent) {
        dragStart = NSEvent.mouseLocation
        windowStart = window?.frame.origin ?? .zero
        dragging = false
    }

    override func mouseDragged(with event: NSEvent) {
        guard let start = dragStart else { return }
        let end = NSEvent.mouseLocation
        let (dx, dy) = (end.x - start.x, end.y - start.y)
        guard dragging || hypot(dx, dy) >= 4 else { return }
        dragging = true
        window?.setFrameOrigin(NSPoint(x: windowStart.x + dx, y: windowStart.y + dy))
    }

    override func mouseUp(with event: NSEvent) {
        defer { dragStart = nil }
        if dragStart != nil && !dragging { onActivate?() }
    }

    override func accessibilityPerformPress() -> Bool {
        onActivate?()
        return true
    }

    private func updateAccessibility() {
        setAccessibilityLabel("\(name)，\(mood.label)")
    }

    private func dot(x: CGFloat, y: CGFloat, size: CGFloat, color: NSColor) {
        color.setFill()
        NSBezierPath(ovalIn: NSRect(x: x, y: y, width: size, height: size)).fill()
    }

    override func draw(_ dirtyRect: NSRect) {
        let reducedMotion = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        let now = ProcessInfo.processInfo.systemUptime
        let elapsed = now - moodSince
        let time = reducedMotion ? 0 : elapsed
        let movement: (CGFloat, CGFloat, CGFloat, CGFloat)
        switch mood {
        case .idle: movement = (0, sin(time * 2.2) * 2.2, sin(time * 1.15) * 1.4, 1)
        case .thinking: movement = (0, sin(time * 3.2) * 3.3, sin(time * 2.7) * 2.0, 1)
        case .done:
            let bounce = time < 1.25 ? abs(sin(time * 8)) * exp(-time * 2.2) : 0
            movement = (0, bounce * 15, bounce * 5, 1 + bounce * 0.06)
        case .error: movement = (sin(time * 25) * max(0, 1 - time) * 4, 0, 0, 1)
        }

        let shadow = NSBezierPath(ovalIn: NSRect(x: 51, y: 34, width: 78, height: 11))
        NSColor.black.withAlphaComponent(0.18).setFill()
        shadow.fill()
        if let artwork = assets?.image(for: mood) {
            NSGraphicsContext.saveGraphicsState()
            let transform = NSAffineTransform()
            transform.translateX(by: 90 + movement.0, yBy: 52 + movement.1)
            transform.rotate(byDegrees: movement.2)
            transform.scale(by: movement.3)
            transform.concat()
            NSGraphicsContext.current?.imageInterpolation = .high
            artwork.draw(in: NSRect(x: -91, y: -27, width: 182, height: 182),
                         from: .zero, operation: .sourceOver, fraction: 1)
            NSGraphicsContext.restoreGraphicsState()
        } else if let icon = NSImage(systemSymbolName: "face.smiling", accessibilityDescription: nil) {
            icon.draw(in: NSRect(x: 57, y: 70, width: 66, height: 66))
        }

        if mood == .thinking {
            for index in 0..<3 {
                let opacity = 0.38 + 0.52 * max(0, sin(time * 5 - Double(index) * 0.8))
                dot(x: 137 + Double(index) * 8, y: 166, size: 4.5, color: mood.tint.withAlphaComponent(opacity))
            }
        } else if mood == .done {
            for (index, point) in [NSPoint(x: 36, y: 138), NSPoint(x: 141, y: 128), NSPoint(x: 147, y: 157)].enumerated() {
                let pulse = max(0, sin(time * 4 + Double(index) + 1))
                let star = NSAttributedString(string: "✦", attributes: [
                    .font: NSFont.systemFont(ofSize: 12 + pulse * 5, weight: .semibold),
                    .foregroundColor: mood.tint.withAlphaComponent(0.54 + 0.45 * pulse)
                ])
                star.draw(at: point)
            }
        }

        let status = NSAttributedString(string: mood.label, attributes: [
            .font: NSFont.systemFont(ofSize: 11, weight: .semibold),
            .foregroundColor: NSColor.white.withAlphaComponent(0.94)
        ])
        let width = status.size().width + 32
        let x = (180 - width) / 2
        let pill = NSBezierPath(roundedRect: NSRect(x: x, y: 7, width: width, height: 24), xRadius: 12, yRadius: 12)
        NSColor(srgbRed: 0.075, green: 0.11, blue: 0.16, alpha: 0.94).setFill()
        pill.fill()
        NSColor.white.withAlphaComponent(0.18).setStroke()
        pill.lineWidth = 1
        pill.stroke()
        dot(x: x + 10, y: 16.5, size: 5, color: mood.tint)
        status.draw(at: NSPoint(x: x + 21, y: 12))
    }
}

final class PetWindow: NSPanel {
    override var canBecomeKey: Bool { true }
}

final class PetApp: NSObject, NSApplicationDelegate {
    private let sprite = OrbitView(frame: NSRect(x: 0, y: 0, width: 180, height: 207))
    private var window: PetWindow!
    private var workbench: NSWindow?
    private var tray: NSStatusItem!
    private var toggle: NSMenuItem!
    private var timer: Timer?
    private var receiver: DispatchSourceRead?
    private var socketFD: Int32 = -1
    private var lockFD: Int32 = -1
    private let directory = "/tmp/agy-hub-pet-\(getuid())"
    private var socketPath: String { directory + "/events.sock" }
    private let activity = LiveActivity()
    private var manual: (Mood, TimeInterval)?
    private var followsHub = true
    private var recent: [(mood: Mood, date: Date)] = []
    private let details = NSPopover()
    private let detailsTitle = NSTextField(labelWithString: "")
    private let connection = NSTextField(labelWithString: "")
    private let countLabel = NSTextField(labelWithString: "")
    private let activityLabel = NSTextField(wrappingLabelWithString: "")
    private var followButton: NSButton!
    private let detailsTime: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter
    }()

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard bindEvents() else {
            NSLog("Orbit Pet could not start its private local event socket.")
            NSApp.terminate(nil)
            return
        }
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1024, height: 640)
        let origin = NSPoint(x: screen.maxX - 192, y: screen.minY + 20)
        window = PetWindow(contentRect: NSRect(origin: origin, size: sprite.frame.size),
                           styleMask: [.borderless, .nonactivatingPanel],
                           backing: .buffered, defer: false)
        window.title = "Orbit Pet"
        window.isReleasedWhenClosed = false
        window.level = .floating
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true
        window.hidesOnDeactivate = false
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.contentView = sprite
        sprite.setAccessibilityElement(true)
        sprite.setAccessibilityRole(.button)
        sprite.setAccessibilityHelp("查看 Hub 状态和桌宠互动，拖动可以移动桌宠。")
        sprite.assets = PetAssets.active()
        sprite.onActivate = { [weak self] in self?.toggleDetails() }
        configureDetails()

        tray = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        tray.button?.image = NSImage(systemSymbolName: "sparkle", accessibilityDescription: "反重力工作台")
        tray.button?.toolTip = "反重力工作台"
        let menu = NSMenu()
        let work = menu.addItem(withTitle: "打开工作台", action: #selector(showWorkbench), keyEquivalent: "")
        work.target = self
        menu.addItem(.separator())
        toggle = menu.addItem(withTitle: "隐藏桌宠", action: #selector(toggleWindow), keyEquivalent: "")
        toggle.target = self
        let showDetails = menu.addItem(withTitle: "活动详情", action: #selector(showDetailsFromMenu), keyEquivalent: "")
        showDetails.target = self
        let demo = NSMenu()
        for mood in [Mood.idle, .thinking, .done, .error] {
            let item = demo.addItem(withTitle: mood.label, action: #selector(demoMood(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = mood.rawValue
        }
        let demos = menu.addItem(withTitle: "演示状态", action: nil, keyEquivalent: "")
        menu.setSubmenu(demo, for: demos)
        menu.addItem(.separator())
        let quit = menu.addItem(withTitle: "退出桌宠", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        quit.target = NSApp
        tray.menu = menu
        sprite.menu = menu
        window.orderFrontRegardless()
        timer = Timer(timeInterval: 1 / 24, repeats: true) { [weak self] _ in self?.refresh() }
        RunLoop.main.add(timer!, forMode: .common)
        if CommandLine.arguments.contains("--workbench") { showWorkbench() }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window?.orderFrontRegardless()
        toggle?.title = "隐藏桌宠"
        return true
    }

    @objc private func toggleWindow() {
        details.performClose(nil)
        if window.isVisible { window.orderOut(nil) } else { window.orderFrontRegardless() }
        toggle.title = window.isVisible ? "隐藏桌宠" : "显示桌宠"
    }

    @objc private func demoMood(_ sender: NSMenuItem) {
        guard let value = sender.representedObject as? String, let mood = Mood(rawValue: value) else { return }
        manual = (mood, ProcessInfo.processInfo.systemUptime + 8)
        refresh()
    }

    private func configureDetails() {
        let controller = NSViewController()
        controller.view = NSView(frame: NSRect(x: 0, y: 0, width: 280, height: 226))
        detailsTitle.font = .systemFont(ofSize: 15, weight: .semibold)
        connection.font = .systemFont(ofSize: 12, weight: .medium)
        connection.textColor = .secondaryLabelColor
        countLabel.font = .systemFont(ofSize: 12)
        activityLabel.font = .monospacedDigitSystemFont(ofSize: 11, weight: .regular)
        activityLabel.textColor = .secondaryLabelColor
        activityLabel.maximumNumberOfLines = 3

        let greet = NSButton(title: "打招呼", target: self, action: #selector(greetPet))
        followButton = NSButton(title: "暂停跟随", target: self, action: #selector(toggleFollowing))
        let open = NSButton(title: "打开 Hub", target: self, action: #selector(openHub))
        let actions = NSStackView(views: [greet, followButton, open])
        actions.orientation = .horizontal
        actions.spacing = 6
        let divider = NSBox()
        divider.boxType = .separator
        let activityTitle = NSTextField(labelWithString: "最近活动")
        activityTitle.font = .systemFont(ofSize: 11, weight: .semibold)
        let stack = NSStackView(views: [detailsTitle, connection, countLabel, divider, activityTitle, activityLabel, actions])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.distribution = .fill
        stack.spacing = 7
        controller.view.addSubview(stack)
        stack.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: controller.view.leadingAnchor, constant: 16),
            stack.trailingAnchor.constraint(equalTo: controller.view.trailingAnchor, constant: -16),
            stack.topAnchor.constraint(equalTo: controller.view.topAnchor, constant: 15),
            divider.widthAnchor.constraint(equalTo: stack.widthAnchor),
            activityLabel.widthAnchor.constraint(lessThanOrEqualTo: stack.widthAnchor),
        ])
        details.contentViewController = controller
        details.contentSize = controller.view.frame.size
        details.behavior = .transient
    }

    private func toggleDetails() {
        if details.isShown {
            details.performClose(nil)
        } else {
            updateDetails()
            details.show(relativeTo: sprite.bounds, of: sprite, preferredEdge: .minX)
        }
    }

    @objc private func showDetailsFromMenu() {
        if !window.isVisible { toggleWindow() }
        if !details.isShown { toggleDetails() }
    }

    @objc private func showWorkbench() {
        details.performClose(nil)
        if workbench == nil {
            workbench = makeWorkbench(activity: activity) { [weak self] in self?.openHub() }
        }
        NSApp.activate(ignoringOtherApps: true)
        workbench?.makeKeyAndOrderFront(nil)
    }

    @objc private func greetPet() {
        manual = (.done, ProcessInfo.processInfo.systemUptime + 2)
        refresh()
        details.performClose(nil)
    }

    @objc private func toggleFollowing() {
        followsHub.toggle()
        manual = nil
        refresh()
        updateDetails()
    }

    @objc private func openHub() {
        guard let app = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.google.antigravity") else {
            NSSound.beep()
            return
        }
        details.performClose(nil)
        NSWorkspace.shared.openApplication(at: app, configuration: .init())
    }

    private func updateDetails() {
        detailsTitle.stringValue = sprite.name
        connection.stringValue = followsHub ? (recent.isEmpty ? "等待 Hub 活动" : "正在跟随 Hub") : "已暂停跟随"
        countLabel.stringValue = "活动中的会话  \(activity.running)"
        followButton.title = followsHub ? "暂停跟随" : "恢复跟随"
        activityLabel.stringValue = recent.isEmpty ? "还没有收到会话事件" : recent.prefix(3).map {
            "\(detailsTime.string(from: $0.date))   \($0.mood.label)"
        }.joined(separator: "\n")
    }

    private func refresh() {
        let now = ProcessInfo.processInfo.systemUptime
        let previousCount = activity.records.count
        activity.expire(now)
        guard window?.isVisible == true else { return }
        let mood: Mood
        if let (selection, expires) = manual, expires > now {
            mood = selection
        } else if !followsHub {
            mood = .idle
        } else {
            mood = activity.spriteMood(uptime: now)
        }
        if mood != sprite.mood || !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion {
            sprite.mood = mood
        }
        if details.isShown && previousCount != activity.records.count { updateDetails() }
    }

    private func bindEvents() -> Bool {
        if mkdir(directory, 0o700) != 0 && errno != EEXIST { return false }
        var info = stat()
        guard lstat(directory, &info) == 0, info.st_uid == getuid(),
              info.st_mode & S_IFMT == S_IFDIR, info.st_mode & 0o077 == 0 else { return false }
        lockFD = open(directory + "/instance.lock", O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard lockFD >= 0, flock(lockFD, LOCK_EX | LOCK_NB) == 0 else { return false }
        socketFD = socket(AF_UNIX, SOCK_DGRAM, 0)
        guard socketFD >= 0, fcntl(socketFD, F_SETFL, O_NONBLOCK) == 0 else { return false }
        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        address.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
        let bytes = Array(socketPath.utf8CString)
        guard bytes.count <= MemoryLayout.size(ofValue: address.sun_path) else { return false }
        withUnsafeMutableBytes(of: &address.sun_path) { target in
            target.copyBytes(from: bytes.map { UInt8(bitPattern: $0) })
        }
        unlink(socketPath)
        let result = withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(socketFD, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard result == 0 else { return false }
        let source = DispatchSource.makeReadSource(fileDescriptor: socketFD, queue: .main)
        source.setEventHandler { [weak self] in self?.receiveEvents() }
        source.resume()
        receiver = source
        return true
    }

    private func receiveEvents() {
        var buffer = [UInt8](repeating: 0, count: 512)
        for _ in 0..<32 {
            let count = recv(socketFD, &buffer, buffer.count, 0)
            if count <= 0 { break }
            let pieces = String(decoding: buffer.prefix(count), as: UTF8.self).split(separator: " ", maxSplits: 2)
            guard pieces.count >= 2 else { continue }
            let session = String(pieces[1])
            if session == "manual" && pieces[0] == "quit" {
                NSApp.terminate(nil)
                return
            }
            if session == "manual" && pieces[0] == "reload" {
                sprite.assets = PetAssets.active()
                NotificationCenter.default.post(name: .orbitAppearanceChanged, object: nil)
                if details.isShown { updateDetails() }
                continue
            }
            if session == "manual" && pieces[0] == "workbench" {
                showWorkbench()
                continue
            }
            guard let mood = Mood(rawValue: String(pieces[0])) else { continue }
            let now = ProcessInfo.processInfo.systemUptime
            if session == "manual" {
                manual = (mood, now + 8)
            } else if session.count == 20 && session.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) {
                let tag = pieces.count == 3 ? WorkspaceTag.decode(pieces[2]) : nil
                let date = Date()
                if activity.record(session, mood: mood, tag: tag, date: date, uptime: now) {
                    recent.insert((mood, date), at: 0)
                    if recent.count > 8 { recent.removeLast() }
                }
            }
        }
        refresh()
        if details.isShown { updateDetails() }
    }

    func applicationWillTerminate(_ notification: Notification) {
        if receiver != nil {
            receiver?.cancel()
            unlink(socketPath)
        }
        if socketFD >= 0 { close(socketFD) }
        if lockFD >= 0 { close(lockFD) }
    }
}

if !runAssetCommand(Array(CommandLine.arguments.dropFirst())) {
    let application = NSApplication.shared
    let delegate = PetApp()
    application.delegate = delegate
    application.setActivationPolicy(.accessory)
    application.run()
}
