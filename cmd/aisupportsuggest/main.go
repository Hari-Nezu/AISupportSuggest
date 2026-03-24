// AISupportSuggest エントリポイント。
// ユーザーの日々の PC 操作ログを収集し、Claude API で分析して業務効率化を提案する。
package main

import (
	"fmt"
	"os"

	"github.com/Hari-Nezu/AISupportSuggest/internal/config"
	"github.com/Hari-Nezu/AISupportSuggest/internal/ui"
)

func main() {
	cfg := config.Load()

	app, err := ui.NewApp(cfg)
	if err != nil {
		fmt.Fprintln(os.Stderr, "起動失敗:", err)
		os.Exit(1)
	}

	// Run() はメインスレッドをブロックする（systray の要件）
	app.Run()
}
