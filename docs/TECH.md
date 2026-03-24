# TECH.md — 技術仕様

> 利用者向けのセットアップ手順は [README.md](../README.md) を参照してください。

---

## アーキテクチャ概要

```
┌──────────────────────────────────────────────────────┐
│  メインプロセス (macOS: NSStatusItem / Windows: tray) │
│                                                      │
│  ┌───────────────┐  1秒ごと   ┌─────────────────┐   │
│  │  ui.App       │ ────────▶ │ EventDetector   │   │
│  │ (tray.go)     │           │ (状態変化検出)    │   │
│  └──────┬────────┘           └────────┬────────┘   │
│         │ 0:00 / 手動                 │ INSERT     │
│         ▼                            ▼            │
│  ┌───────────────┐           ┌────────────────┐   │
│  │   Analyzer    │◀──────────│   SQLite DB    │   │
│  │ Phase1→Phase2 │           │  activity.db   │   │
│  └──────┬────────┘           └────────────────┘   │
│         │ prompt                                  │
│         ▼                                         │
│  ┌───────────────┐                                │
│  │  llm.Client   │──▶ Anthropic API / Ollama      │
│  └──────┬────────┘                                │
│         │ result (DB に保存)                       │
│         ▼                                         │
│  ┌─────────────────────────────┐                  │
│  │ bin/SuggestionViewer(Swift) │                  │
│  │ または ブラウザ（HTML）       │                  │
│  └─────────────────────────────┘                  │
└──────────────────────────────────────────────────────┘
```

---

## ファイル構成

```
AISupportSuggest/
├── cmd/aisupportsuggest/
│   └── main.go                  # エントリポイント
├── internal/
│   ├── config/config.go         # 設定値（環境変数・デフォルト値）
│   ├── database/db.go           # SQLite CRUD（modernc.org/sqlite）
│   ├── detector/
│   │   ├── detector.go          # 監視ループ（共通）
│   │   ├── detector_darwin.go   # macOS: osascript 経由
│   │   └── detector_windows.go  # Windows: Win32 API syscall
│   ├── llm/client.go            # Anthropic / Ollama クライアント
│   ├── analyzer/
│   │   ├── analyzer.go          # 2段階分析オーケストレーション
│   │   └── prompts.go           # プロンプトテンプレート
│   └── ui/
│       ├── tray.go              # systray メニューバー/トレイ
│       ├── viewer.go            # Swift ビューア or ブラウザ表示
│       ├── alert_darwin.go      # osascript ダイアログ
│       └── alert_windows.go     # MessageBox API
├── SuggestionViewer.swift        # macOS 提案表示ビューア（AppKit）
├── data/                         # 自動生成・.gitignore対象
│   └── activity.db
├── bin/                          # ビルド成果物・.gitignore対象
│   ├── aisupportsuggest
│   └── SuggestionViewer
├── docs/TECH.md
├── scripts/
│   ├── setup.sh
│   └── setup.bat
└── go.mod / go.sum
```

---

## イベント駆動型ログ（設計思想）

### イベントタイプ

| event_type | 発生条件 |
|---|---|
| `app_switch` | アクティブアプリが変わった |
| `window_change` | 同アプリ内でウィンドウタイトルが変わった |
| `idle_start` | `IDLE_THRESHOLD_SEC`（デフォルト5分）変化なし |
| `idle_end` | idle 状態から復帰 |

### duration の表示方針

LLM がイベントの重みを正確に読み取れるよう、プロンプト整形時に以下のルールを適用する。

| 秒数 | 表示 |
|---|---|
| 0 以下 | 表示なし（最後のイベントなど未確定） |
| 3秒未満 | `(一瞬)` |
| 3〜59秒 | `(X秒)` |
| 1〜59分 | `(X分)` |
| 1時間以上 | `(X.X時間)` |

「一瞬映っただけ」と「30分作業」を同等に扱わないことで、Phase 1 の意味付け精度が向上する。

### 分析で抽出可能な特徴量

- **アプリ使用時間分布**: 各アプリの合計 `duration_seconds`
- **コンテキストスイッチ頻度**: 単位時間あたりの `app_switch` 数
- **遷移パターン**: アプリ A → B の遷移確率（マルコフ連鎖）
- **集中度指標**: 連続使用時間の中央値・最大値
- **idle 比率**: 実作業時間 vs 離席時間

---

## データベーススキーマ

### `events` テーブル

```sql
CREATE TABLE events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT    NOT NULL,       -- ISO 8601
    event_type       TEXT    NOT NULL,       -- app_switch | window_change | idle_start | idle_end
    app_name         TEXT    NOT NULL,
    window_title     TEXT    DEFAULT '',
    duration_seconds REAL,                   -- 次のイベントまでの持続時間（秒）
    created_at       TEXT    NOT NULL
);
```

### `daily_analysis` テーブル

```sql
CREATE TABLE daily_analysis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT    NOT NULL,          -- YYYY-MM-DD
    phase         TEXT    NOT NULL,          -- 'semantic' | 'optimization'
    event_count   INTEGER DEFAULT 0,
    app_summary   TEXT,                      -- JSON: {"app": total_seconds}
    analysis_text TEXT,                      -- LLM の分析結果全文
    created_at    TEXT    NOT NULL,
    UNIQUE(date, phase)                      -- 再分析時は UPSERT で上書き
);
```

---

## 2段階分析パイプライン

### Phase 1: semantic（意味付け）

イベントログを LLM に渡し、各作業セッションの「意味」を推定する。

**入力例:**
```
14:00:05 → アプリ切替: Visual Studio Code - main.go (23分)
14:23:20   ウィンドウ変更: Visual Studio Code - config.go (一瞬)
14:25:02 → アプリ切替: Chrome - Gmail (47秒)
14:25:49 → アプリ切替: Chrome - Google Drive (1分)
14:27:17 → アプリ切替: Chrome - Gmail - 新規メール作成 (3分)
```

**出力例:**
```
セッション1: 14:00〜14:23 — コード開発（main.go, config.go の編集）
セッション2: 14:23〜14:31 — メール作成のための資料収集
  → Gmail確認 → Google Drive で資料を探す → Gmail に戻ってメール作成
  推定: 「メールに添付する資料を Drive で探していた」
```

結果は `daily_analysis` テーブルに `phase='semantic'` で保存。

### Phase 2: optimization（ワークロード高速化提案）

Phase 1 の結果 + アプリ使用統計を入力に、5つの観点で改善提案を生成。

1. 自動化可能な繰り返し作業
2. AI で代替・補助できる作業
3. ツール統合による効率化
4. ワークフロー改善（作業順序・バッチ化等）
5. 具体的なツール・設定の推奨

結果は `daily_analysis` テーブルに `phase='optimization'` で保存。

---

## 設定値一覧（環境変数）

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `ANTHROPIC_API_KEY` | — | Anthropic API キー |
| `USE_ANTHROPIC` | `true` | `false` で Ollama に切替 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama エンドポイント |
| `OLLAMA_MODEL` | `llama3.2` | 使用モデル名 |
| `POLL_INTERVAL_SEC` | `1` | ポーリング間隔（秒） |
| `IDLE_THRESHOLD_SEC` | `300` | idle 判定閾値（秒） |
| `RECORD_ONLY` | `false` | 記録のみモード（LLM 呼び出しをスキップ） |
| `ANALYSIS_HOUR` | `0` | 自動分析の実行時（0〜23） |
| `ANALYSIS_MINUTE` | `0` | 自動分析の実行分 |
| `DB_PATH` | `data/activity.db` | DB ファイルパス |

---

## 依存ライブラリ

| パッケージ | 用途 |
|-----------|------|
| `github.com/getlantern/systray` | メニューバー / システムトレイ（macOS・Windows） |
| `modernc.org/sqlite` | SQLite ドライバー（pure Go・CGo 不要） |

---

## 既知の制限

- **AppleScript の権限**: macOS のオートメーション許可が必要。なければ `Unknown` が記録される
- **スリープ中**: goroutine が停止するためログは記録されない
- **DB ローテーション**: 自動なし。長期利用時は `data/activity.db` を手動管理
