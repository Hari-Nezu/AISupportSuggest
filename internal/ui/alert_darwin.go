//go:build darwin

// macOS のアラートダイアログ。osascript 経由で表示する。
package ui

import (
	"fmt"
	"os/exec"
)

func showAlert(title, message string) {
	script := fmt.Sprintf(
		`display dialog %q with title %q buttons {"OK"} default button "OK"`,
		message, title,
	)
	exec.Command("osascript", "-e", script).Start() //nolint:errcheck
}
