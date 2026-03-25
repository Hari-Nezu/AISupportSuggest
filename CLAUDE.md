# AISupportSuggest

ユーザーの日々のPC操作ログを収集し、Claude API で分析して業務効率化を提案する macOS / Windows デスクトップアプリ。
**実装言語: Go**（旧 Python から全面書き換え済み）

## アーキテクチャ概要

```
cmd/aisupportsuggest/main.go
└── internal/ui/tray.go        (systray メニューバー/トレイ、macOS・Windows 共通)
      ├── detector.go           — アクティブウィンドウを1秒ポーリングで監視・DB 記録
      │     ├── detector_darwin.go    (osascript 経由)
      │     └── detector_windows.go  (Win32 API syscall)
      ├── database/db.go        — SQLite (data/activity.db) への読み書き
      ├── analyzer/analyzer.go  — 2段階 LLM 分析パイプライン
      │     Phase 1 semantic    : イベントログ → 作業の意味付け
      │     Phase 2 optimization: 意味付け → 省力化提案
      ├── analyzer/prompts.go   — LLM プロンプトテンプレート
      ├── llm/client.go         — Anthropic / Ollama 切替クライアント
      └── ui/viewer.go          — 分析結果表示（Swift or ブラウザ）
```

## 主要モジュール

| ファイル | 役割 |
|---|---|
| `internal/config/config.go` | 全設定値（環境変数・デフォルト値） |
| `internal/detector/detector.go` | 監視ループ（共通）・idle 検出 |
| `internal/database/db.go` | スレッドセーフ SQLite ラッパー |
| `internal/analyzer/analyzer.go` | Phase 1→Phase 2 の分析オーケストレーション |
| `internal/analyzer/prompts.go` | LLM プロンプトテンプレート |
| `internal/llm/client.go` | Anthropic / Ollama クライアント |
| `internal/ui/tray.go` | systray メニューバー/トレイ UI |
| `internal/ui/viewer.go` | Swift ビューア or ブラウザ表示 |
| `SuggestionViewer.swift` | 提案表示（AppKit ネイティブ、優先使用） |

## セットアップ

```sh
bash scripts/setup.sh        # ビルド + Swift ビューアビルド
export ANTHROPIC_API_KEY='sk-ant-...'
./bin/aisupportsuggest
```

## 設定（環境変数）

| 変数 | デフォルト | 説明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Anthropic API キー |
| `USE_ANTHROPIC` | `true` | `false` で Ollama に切替 |
| `RECORD_ONLY` | `false` | `true` にすると LLM 呼び出しをスキップし記録のみ |
| `ANALYSIS_HOUR/MINUTE` | `0:00` | 毎日の自動分析時刻 |
| `IDLE_THRESHOLD_SEC` | `300` | idle 判定閾値（秒） |
| `DB_PATH` | `data/activity.db` | DB ファイルパス |

全設定値は `docs/TECH.md` の「設定値一覧」を参照。

## 提案ビューア（2段階フォールバック）

1. `bin/SuggestionViewer`（Swift/AppKit）が存在すれば優先使用
2. なければ `internal/ui/viewer.go` からブラウザで一時 HTML を表示

Swift ビューアのビルド:
```sh
swiftc SuggestionViewer.swift -o bin/SuggestionViewer
```

`bin/` は `.gitignore` 対象のためコミット不要。

## DB スキーマ

```sql
events (id, timestamp, event_type, app_name, window_title, duration_seconds, created_at)
daily_analysis (id, date, phase, event_count, app_summary, analysis_text, created_at)
```

`event_type`: `app_switch` | `window_change` | `idle_start` | `idle_end`

## コーディング規約

- コメント・ドキュメントは日本語
- 新しい設定値は必ず `internal/config/config.go` に集約する
- LLM プロンプトは `internal/analyzer/prompts.go` に集約する
- プラットフォーム固有コードはビルドタグ（`_darwin.go` / `_windows.go`）で分離する
