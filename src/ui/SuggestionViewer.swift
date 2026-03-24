// AI省力化提案ビューア
// ビルド: swiftc src/ui/SuggestionViewer.swift -o bin/SuggestionViewer
// 使用:  bin/SuggestionViewer <テキストファイルパス>

import AppKit

// MARK: - AppDelegate

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private let text: String

    init(text: String) {
        self.text = text
        super.init()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildWindow()
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    // MARK: - UI

    private func buildWindow() {
        let w = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 680, height: 520),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        w.title = "AI省力化提案"
        w.center()
        w.isReleasedWhenClosed = false

        let bg = NSColor(red: 0x1e/255, green: 0x1e/255, blue: 0x2e/255, alpha: 1)
        w.backgroundColor = bg

        let container = NSView()
        container.translatesAutoresizingMaskIntoConstraints = false
        w.contentView = container

        // ── ヘッダー ──
        let header = NSTextField(labelWithString: "AI省力化提案")
        header.translatesAutoresizingMaskIntoConstraints = false
        header.font = .boldSystemFont(ofSize: 17)
        header.textColor = NSColor(red: 0xcd/255, green: 0xd6/255, blue: 0xf4/255, alpha: 1)
        header.backgroundColor = .clear
        container.addSubview(header)

        // ── スクロールビュー + テキストビュー ──
        let scrollView = NSScrollView()
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.wantsLayer = true
        scrollView.layer?.cornerRadius = 8
        scrollView.backgroundColor = NSColor(red: 0x31/255, green: 0x32/255, blue: 0x44/255, alpha: 1)
        container.addSubview(scrollView)

        let textView = NSTextView()
        textView.isEditable = false
        textView.isSelectable = true
        textView.string = text
        textView.font = .systemFont(ofSize: 13)
        textView.textColor = NSColor(red: 0xcd/255, green: 0xd6/255, blue: 0xf4/255, alpha: 1)
        textView.backgroundColor = .clear
        textView.textContainerInset = NSSize(width: 14, height: 12)
        scrollView.documentView = textView
        scrollView.contentView.scroll(to: .zero)

        // ── 閉じるボタン ──
        let btn = NSButton(title: "閉じる", target: self, action: #selector(closeWindow))
        btn.translatesAutoresizingMaskIntoConstraints = false
        btn.bezelStyle = .rounded
        btn.wantsLayer = true
        btn.layer?.backgroundColor = NSColor(red: 0x89/255, green: 0xb4/255, blue: 0xfa/255, alpha: 1).cgColor
        btn.layer?.cornerRadius = 6
        btn.contentTintColor = NSColor(red: 0x1e/255, green: 0x1e/255, blue: 0x2e/255, alpha: 1)
        btn.font = .boldSystemFont(ofSize: 12)
        container.addSubview(btn)

        // ── Auto Layout ──
        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: container.topAnchor, constant: 16),
            header.centerXAnchor.constraint(equalTo: container.centerXAnchor),

            scrollView.topAnchor.constraint(equalTo: header.bottomAnchor, constant: 12),
            scrollView.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 16),
            scrollView.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -16),
            scrollView.bottomAnchor.constraint(equalTo: btn.topAnchor, constant: -12),

            btn.centerXAnchor.constraint(equalTo: container.centerXAnchor),
            btn.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -14),
            btn.widthAnchor.constraint(greaterThanOrEqualToConstant: 96),
        ])

        w.makeKeyAndOrderFront(nil)
        self.window = w
    }

    @objc private func closeWindow() {
        window.close()
    }
}

// MARK: - Entry point

guard CommandLine.arguments.count >= 2 else {
    fputs("Usage: SuggestionViewer <text_file_path>\n", stderr)
    exit(1)
}

let filePath = CommandLine.arguments[1]
let content: String
do {
    content = try String(contentsOfFile: filePath, encoding: .utf8)
} catch {
    fputs("ファイルの読み込みに失敗しました: \(error)\n", stderr)
    exit(1)
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate(text: content)
app.delegate = delegate
app.run()
