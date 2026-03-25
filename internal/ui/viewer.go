// 分析結果表示ビューア。
// Swift ビューアバイナリが存在すれば優先使用し、なければ一時 HTML をブラウザで開く。
package ui

import (
	"fmt"
	"html"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

// OpenViewer は分析結果テキストを表示する。
// 優先順: bin/SuggestionViewer（Swift） > ブラウザ（一時 HTML）
func OpenViewer(result string) error {
	// 実行ファイルと同じディレクトリの SuggestionViewer を探す
	exePath, _ := os.Executable()
	swiftBin := filepath.Join(filepath.Dir(exePath), "SuggestionViewer")

	if _, err := os.Stat(swiftBin); err == nil {
		return openSwiftViewer(swiftBin, result)
	}
	return openBrowserViewer(result)
}

func openSwiftViewer(binPath, result string) error {
	f, err := writeTempFile(result, "*.txt")
	if err != nil {
		return err
	}
	cmd := exec.Command(binPath, f)
	cmd.Start() //nolint:errcheck // バックグラウンドで開く
	return nil
}

func openBrowserViewer(result string) error {
	htmlContent := buildHTML(result)
	f, err := writeTempFile(htmlContent, "*.html")
	if err != nil {
		return err
	}
	return openBrowser("file://" + f)
}

func openBrowser(url string) error {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("open", url)
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	return cmd.Start()
}

func writeTempFile(content, pattern string) (string, error) {
	f, err := os.CreateTemp("", "aisupport-"+pattern)
	if err != nil {
		return "", fmt.Errorf("一時ファイル作成失敗: %w", err)
	}
	defer f.Close()
	if _, err := f.WriteString(content); err != nil {
		return "", err
	}
	return f.Name(), nil
}

func buildHTML(markdownLike string) string {
	lines := strings.Split(markdownLike, "\n")
	var sb strings.Builder
	sb.WriteString(`<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<title>AI省力化提案</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       max-width:860px;margin:40px auto;padding:0 24px;line-height:1.7;color:#222}
  h1{color:#1a1a1a;border-bottom:2px solid #e0e0e0;padding-bottom:8px}
  h2{color:#333;margin-top:2em}
  hr{border:none;border-top:1px solid #e0e0e0;margin:2em 0}
  strong{color:#111}
  pre{background:#f5f5f5;padding:12px;border-radius:6px;overflow-x:auto}
</style></head><body>`)
	for _, line := range lines {
		escaped := html.EscapeString(line)
		switch {
		case strings.HasPrefix(line, "# "):
			sb.WriteString("<h1>" + escaped[2:] + "</h1>\n")
		case strings.HasPrefix(line, "## "):
			sb.WriteString("<h2>" + escaped[3:] + "</h2>\n")
		case strings.HasPrefix(line, "### "):
			sb.WriteString("<h3>" + escaped[4:] + "</h3>\n")
		case line == "---":
			sb.WriteString("<hr>\n")
		case line == "":
			sb.WriteString("<br>\n")
		default:
			sb.WriteString("<p>" + escaped + "</p>\n")
		}
	}
	sb.WriteString("</body></html>")
	return sb.String()
}
