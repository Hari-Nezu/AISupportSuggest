// システムトレイ / メニューバー UI。
// github.com/getlantern/systray を使用し、macOS / Windows 両対応。
package ui

import (
	"fmt"
	"time"

	"github.com/getlantern/systray"

	"github.com/Hari-Nezu/AISupportSuggest/internal/analyzer"
	"github.com/Hari-Nezu/AISupportSuggest/internal/config"
	"github.com/Hari-Nezu/AISupportSuggest/internal/database"
	"github.com/Hari-Nezu/AISupportSuggest/internal/detector"
	"github.com/Hari-Nezu/AISupportSuggest/internal/llm"
)

// App はトレイアプリの状態を保持する。
type App struct {
	cfg      *config.Config
	db       *database.DB
	det      *detector.EventDetector
	analyzer *analyzer.Analyzer
}

// NewApp は App を初期化して返す。
func NewApp(cfg *config.Config) (*App, error) {
	db, err := database.Open(cfg.DBPath)
	if err != nil {
		return nil, fmt.Errorf("DB オープン失敗: %w", err)
	}
	llmClient := llm.New(cfg)
	det := detector.New(db, cfg.PollIntervalSec, cfg.IdleThresholdSec)
	az := analyzer.New(db, llmClient)
	return &App{cfg: cfg, db: db, det: det, analyzer: az}, nil
}

// Run はトレイを起動する（メインスレッドをブロックする）。
func (a *App) Run() {
	systray.Run(a.onReady, a.onExit)
}

func (a *App) onReady() {
	title := "AI"
	if a.cfg.RecordOnly {
		title = "録"
	}
	systray.SetTitle(title)
	systray.SetTooltip("AISupportSuggest")

	analyzeLabel := "今すぐ分析する"
	if a.cfg.RecordOnly {
		analyzeLabel = "今日のログを確認する"
	}

	mLogCount := systray.AddMenuItem("今日のログ件数を確認", "今日記録されたイベント数を表示")
	mAnalyze := systray.AddMenuItem(analyzeLabel, "LLM 分析を実行して提案を表示")
	systray.AddSeparator()
	mQuit := systray.AddMenuItem("終了", "アプリを終了する")

	// イベント検出を開始
	a.det.Start()

	// スケジューラを起動
	go a.runScheduler()

	// メニューイベントループ
	go func() {
		for {
			select {
			case <-mLogCount.ClickedCh:
				a.showLogCount()
			case <-mAnalyze.ClickedCh:
				go a.runAnalysis()
			case <-mQuit.ClickedCh:
				systray.Quit()
			}
		}
	}()
}

func (a *App) onExit() {
	a.det.Stop()
	a.db.Close()
}

// ── ロジック ──────────────────────────────────────────────────────────────────

func (a *App) showLogCount() {
	n, err := a.db.GetTodayEventCount()
	if err != nil {
		showAlert("エラー", err.Error())
		return
	}
	showAlert("今日の活動ログ", fmt.Sprintf("イベント数: %d 件", n))
}

func (a *App) runAnalysis() {
	result, err := a.analyzer.AnalyzeToday()
	if err != nil {
		showAlert("分析エラー", err.Error())
		return
	}
	if err := OpenViewer(result); err != nil {
		showAlert("表示エラー", err.Error())
	}
}

// runScheduler は毎日指定時刻に自動分析を実行する。
func (a *App) runScheduler() {
	for {
		now := time.Now()
		next := time.Date(
			now.Year(), now.Month(), now.Day(),
			a.cfg.AnalysisHour, a.cfg.AnalysisMinute, 0, 0, now.Location(),
		)
		if !next.After(now) {
			next = next.Add(24 * time.Hour)
		}
		time.Sleep(time.Until(next))
		go a.runAnalysis()
	}
}
