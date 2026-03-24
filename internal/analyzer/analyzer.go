// 分析オーケストレーション。
// Phase 1 (semantic):     イベントログ → 作業の意味付け
// Phase 2 (optimization): 意味付けデータ → ワークロード高速化提案
package analyzer

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/Hari-Nezu/AISupportSuggest/internal/database"
	"github.com/Hari-Nezu/AISupportSuggest/internal/llm"
)

// Analyzer は2段階 LLM 分析パイプラインを実行する。
type Analyzer struct {
	db  *database.DB
	llm *llm.Client
}

// New は新しい Analyzer を返す。
func New(db *database.DB, llmClient *llm.Client) *Analyzer {
	return &Analyzer{db: db, llm: llmClient}
}

// AnalyzeToday は今日のイベントを分析して結果テキストを返す。
func (a *Analyzer) AnalyzeToday() (string, error) {
	today := time.Now().Format("2006-01-02")

	events, err := a.db.GetEventsByDate(today)
	if err != nil {
		return "", fmt.Errorf("イベント取得失敗: %w", err)
	}
	if len(events) == 0 {
		return "今日のイベントログがありません。\nアプリを起動してしばらく操作すると、イベントが記録されます。", nil
	}

	appSummary, err := a.db.GetAppSummary(today)
	if err != nil {
		return "", fmt.Errorf("アプリ集計失敗: %w", err)
	}

	eventText := FormatEventsForPrompt(events)
	appSummaryText := FormatAppSummary(appSummary)
	appSummaryJSON, _ := json.Marshal(appSummary)

	// ── Phase 1: semantic（意味付け）─────────────────────────────────────
	semanticResult, err := a.llm.Query(BuildSemanticPrompt(today, eventText))
	if err != nil {
		return "", fmt.Errorf("Phase 1 失敗: %w", err)
	}
	if err := a.db.SaveAnalysis(today, "semantic", semanticResult, string(appSummaryJSON), len(events)); err != nil {
		return "", fmt.Errorf("Phase 1 保存失敗: %w", err)
	}

	// ── Phase 2: optimization（高速化提案）──────────────────────────────
	optimizationResult, err := a.llm.Query(BuildOptimizationPrompt(today, semanticResult, appSummaryText))
	if err != nil {
		return "", fmt.Errorf("Phase 2 失敗: %w", err)
	}
	if err := a.db.SaveAnalysis(today, "optimization", optimizationResult, string(appSummaryJSON), len(events)); err != nil {
		return "", fmt.Errorf("Phase 2 保存失敗: %w", err)
	}

	return fmt.Sprintf(
		"# %s の分析結果\n\n---\n\n# Phase 1: 作業の意味付け\n\n%s\n\n---\n\n# Phase 2: ワークロード高速化提案\n\n%s",
		today, semanticResult, optimizationResult,
	), nil
}

// RecordOnlySummary は RECORD_ONLY モード時のテキスト要約を返す。
func RecordOnlySummary(events []database.Event, appSummary map[string]float64) string {
	date := time.Now().Format("2006年01月02日")
	return fmt.Sprintf(
		"## 記録モード — %s\nイベント数: %d 件\n\n### アプリ別使用時間\n%s\n\n### 直近のイベント（最新20件）\n%s\n\n---\n※ RECORD_ONLY モードのため LLM 分析はスキップされました。",
		date,
		len(events),
		FormatAppSummary(appSummary),
		FormatEventsForPrompt(tail(events, 20)),
	)
}

func tail(events []database.Event, n int) []database.Event {
	if len(events) <= n {
		return events
	}
	return events[len(events)-n:]
}
