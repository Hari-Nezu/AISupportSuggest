# AISupportSuggest

ユーザーの日々のPC操作ログを収集し、Claude API で分析して業務効率化を提案する macOS / Windows デスクトップアプリ。

## アーキテクチャ概要

```
main.py
└── macOS: src/ui/menubar_app.py   (rumps メニューバーアプリ)
└── Windows: src/ui/tray_app_win.py (pystray トレイアプリ)
      ├── EventDetector   — アクティブウィンドウを1秒ポーリングで監視・DB 記録
      ├── Database        — SQLite (data/activity.db) への読み書き
      ├── Analyzer        — 2段階 LLM 分析パイプライン
      │     Phase 1 semantic    : イベントログ → 作業の意味付け
      │     Phase 2 optimization: 意味付け → 省力化提案
      └── SuggestionViewer — 分析結果表示ウィンドウ（別プロセス）
```

### 主要モジュール

| ファイル | 役割 |
|---|---|
| `src/config.py` | 全設定値（API キー・モード・閾値）をここで管理 |
| `src/event_detector.py` | アクティブウィンドウ取得・イベント記録・idle 検出 |
| `src/database.py` | スレッドセーフ SQLite ラッパー。`events` / `daily_analysis` テーブル |
| `src/analyzer.py` | Phase 1→Phase 2 の分析オーケストレーション |
| `src/prompts.py` | LLM プロンプトテンプレート |
| `src/llm_client.py` | Anthropic / Ollama 切替クライアント |
| `src/screenshot.py` | スクリーンショット撮影 |
| `src/ui/menubar_app.py` | macOS メニューバー UI |
| `src/ui/tray_app_win.py` | Windows トレイ UI |
| `src/ui/suggestion_viewer.py` | 提案表示（Python フォールバック、webbrowser 使用） |
| `src/ui/SuggestionViewer.swift` | 提案表示（AppKit ネイティブ、優先使用） |

## セットアップ

```sh
bash scripts/setup.sh        # 依存インストール + Swift ビューアビルド
export ANTHROPIC_API_KEY='sk-ant-...'
python3 main.py
```

## 動作モード（`src/config.py` で切替）

| 変数 | デフォルト | 説明 |
|---|---|---|
| `RECORD_ONLY` | `False` | `True` にすると LLM 呼び出しをスキップし記録のみ |
| `SCREENSHOT_MODE` | `False` | `True` にするとアプリ切替時にスクショ撮影 |
| `USE_ANTHROPIC` | `True` | `False` にすると Ollama を使用 |
| `ANALYSIS_HOUR/MINUTE` | `0:00` | 毎日の自動分析時刻 |

## 提案ビューア（2段階フォールバック）

1. `bin/SuggestionViewer`（Swift/AppKit）が存在すれば優先使用
2. なければ `src/ui/suggestion_viewer.py`（webbrowser + 一時 HTML）にフォールバック

Swift ビューアのビルド:
```sh
swiftc src/ui/SuggestionViewer.swift -o bin/SuggestionViewer
```

`bin/` は `.gitignore` 対象のためコミット不要。

## DB スキーマ

```sql
events (id, timestamp, event_type, app_name, window_title, screenshot_path, duration_seconds)
daily_analysis (id, date, phase, event_count, app_summary, analysis_text)
```

`event_type`: `app_switch` | `window_change` | `idle_start` | `idle_end`

## コーディング規約

- コメント・ドキュメントは日本語
- 型ヒントを使用（Python 3.9+ 互換）
- 新しい設定値は必ず `src/config.py` に集約する
- LLM プロンプトは `src/prompts.py` に集約する
