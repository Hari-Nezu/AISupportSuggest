// LLM プロンプトテンプレート。
// Phase 1: semantic  — イベントログから作業の意味付けを行う
// Phase 2: optimization — 意味付けデータからワークロード高速化を提案する
package analyzer

import (
	"fmt"
	"strings"

	"github.com/Hari-Nezu/AISupportSuggest/internal/database"
)

// BuildSemanticPrompt は Phase 1 用プロンプトを生成する。
func BuildSemanticPrompt(date, eventLogText string) string {
	return fmt.Sprintf(`あなたはユーザーのPC作業パターンを分析する専門家です。
以下は %s のイベントログです。各行は「アプリの切り替え」や「ウィンドウの変更」が
発生した瞬間を記録しています。

=== イベントログ ===
%s
===================

このログを分析し、以下の形式で「意味付け」を行ってください。
必ず日本語で回答してください。

## 1. 作業セッション一覧

各セッション（関連する一連の操作）について:
- **時間帯**: HH:MM 〜 HH:MM
- **使用アプリ**: アプリ名とコンテキスト
- **推定作業内容**: 具体的に何をしていたか推定（例:「メールを作るためにGoogle Driveで資料を調べていた」）
- **作業の流れ**: 前後のセッションとの関連

## 2. 1日の作業パターン要約

- 主な作業カテゴリとその時間割合
- 集中していた時間帯（長時間の単一アプリ使用）
- 分散していた時間帯（頻繁なアプリ切り替え）
- よくあるアプリ遷移パターン（例: Slack → Chrome → VSCode）

## 3. 特記事項

- コンテキストスイッチが多い時間帯とその原因推定
- 非効率な可能性がある操作パターン
- 長時間のidle（離席・休憩と推定）`, date, eventLogText)
}

// BuildOptimizationPrompt は Phase 2 用プロンプトを生成する。
func BuildOptimizationPrompt(date, semanticText, appSummaryText string) string {
	return fmt.Sprintf(`あなたは業務効率化の専門コンサルタントです。
以下は %s のユーザーの作業分析データです。

=== アプリ使用時間 ===
%s

=== 作業の意味付け分析 ===
%s
======================

この分析データをもとに、ユーザーのワークフローを高速化・省力化する提案を行ってください。
必ず日本語で回答し、以下の5つの観点から具体的に提案してください。

## 1. 自動化可能な繰り返し作業

今日のログで繰り返し発生していた操作パターンを特定し、
自動化する具体的な方法を提案してください。
（例: Zapier、Power Automate、シェルスクリプト等）

## 2. AIで代替・補助できる作業

LLM（Claude、ChatGPT等）やAIツールで高速化できる作業を特定してください。
- テキスト作成・要約・翻訳
- コードレビュー・生成
- データ整理・分析
- メール・メッセージのドラフト作成

## 3. ツール統合による効率化

複数アプリを行き来していた作業について、
ツールの統合や代替で効率化できるものを提案してください。

## 4. ワークフロー改善

作業順序の改善、バッチ処理化、時間帯の最適化など、
作業の進め方自体を改善する提案をしてください。

## 5. 具体的なツール・設定の推奨

上記の提案を実現するための具体的なツール名、設定方法、
導入ステップを示してください。無料ツールを優先してください。

---

各提案は以下の形式で書いてください:

**【提案タイトル】**
- 現在の状況: （今日のログからの具体的な根拠）
- 改善案: （何をどうするか）
- 使えるツール: （具体名）
- 期待効果: （どれくらい時間短縮/省力化できるか）`, date, appSummaryText, semanticText)
}

// FormatEventsForPrompt はイベント一覧をプロンプト用テキストに整形する。
// duration が短い場合は「一瞬」と明示し、LLM が滞在時間を正確に読み取れるようにする。
func FormatEventsForPrompt(events []database.Event) string {
	lines := make([]string, 0, len(events))
	for _, e := range events {
		// ISO 形式から HH:MM:SS を抽出
		timePart := e.Timestamp
		if len(e.Timestamp) >= 19 {
			timePart = e.Timestamp[11:19]
		}

		typeLabel := map[string]string{
			"app_switch":    "→ アプリ切替",
			"window_change": "  ウィンドウ変更",
			"idle_start":    "⏸ idle開始",
			"idle_end":      "▶ idle復帰",
		}[e.EventType]
		if typeLabel == "" {
			typeLabel = e.EventType
		}

		durStr := formatDuration(e.DurationSeconds)

		line := fmt.Sprintf("%s %s: %s", timePart, typeLabel, e.AppName)
		if e.WindowTitle != "" {
			line += " - " + e.WindowTitle
		}
		line += durStr
		lines = append(lines, line)
	}
	return strings.Join(lines, "\n")
}

// formatDuration は秒数を LLM が読みやすい文字列に変換する。
// 3秒未満は「一瞬」と表示することで、流し見と集中作業の区別を明確にする。
func formatDuration(sec float64) string {
	switch {
	case sec <= 0:
		return ""
	case sec < 3:
		return " (一瞬)"
	case sec < 60:
		return fmt.Sprintf(" (%.0f秒)", sec)
	case sec < 3600:
		return fmt.Sprintf(" (%.0f分)", sec/60)
	default:
		return fmt.Sprintf(" (%.1f時間)", sec/3600)
	}
}

// FormatAppSummary はアプリ別使用時間をプロンプト用テキストに整形する。
func FormatAppSummary(summary map[string]float64) string {
	if len(summary) == 0 {
		return "（データなし）"
	}
	lines := make([]string, 0, len(summary))
	for app, sec := range summary {
		min := sec / 60
		var s string
		switch {
		case min >= 60:
			s = fmt.Sprintf("- %s: %.1f時間", app, min/60)
		case min >= 1:
			s = fmt.Sprintf("- %s: %.0f分", app, min)
		default:
			s = fmt.Sprintf("- %s: %.0f秒", app, sec)
		}
		lines = append(lines, s)
	}
	return strings.Join(lines, "\n")
}
