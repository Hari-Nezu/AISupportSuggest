//go:build darwin

// macOS のアクティブウィンドウ取得。osascript 経由で Accessibility API を使用する。
package detector

import (
	"os/exec"
	"strings"
)

const appleScript = `
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
    set frontWindow to ""
    try
        set frontWindow to name of first window of (first application process whose frontmost is true)
    end try
    return frontApp & "|||" & frontWindow
end tell
`

// GetActiveWindow は macOS でフォアグラウンドのアプリ名とウィンドウタイトルを返す。
func GetActiveWindow() (app, window string) {
	out, err := exec.Command("osascript", "-e", appleScript).Output()
	if err != nil {
		return "Unknown", ""
	}
	parts := strings.SplitN(strings.TrimSpace(string(out)), "|||", 2)
	app = strings.TrimSpace(parts[0])
	if len(parts) > 1 {
		window = strings.TrimSpace(parts[1])
	}
	if app == "" {
		app = "Unknown"
	}
	return app, window
}
