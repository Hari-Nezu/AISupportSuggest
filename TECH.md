# TECH.md — 技術仕様

> 利用者向けのセットアップ手順は [README.md](./README.md) を参照してください。

---

## アーキテクチャ概要

```
┌──────────────────────────────────────────────────────┐
│  メインプロセス (macOS: rumps / Windows: pystray)      │
│                                                      │
│  ┌───────────────┐  1秒ごと   ┌─────────────────┐   │
│  │ UI App        │ ────────▶ │ EventDetector   │   │
│  │ (menubar/tray)│           │ (状態変化検出)    │   │
│  └──────┬────────┘           └────────┬────────┘   │
│         │ 0:00 / 手動                 │ INSERT     │
│         ▼                            ▼            │
│  ┌───────────────┐           ┌────────────────┐   │
│  │   analyzer    │◀──────────│  SQLite DB     │   │
│  │ Phase1→Phase2 │           │ activity.db    │   │
│  └──────┬────────┘           └────────────────┘   │
│         │ prompt                                  │
│         ▼                                         │
│  ┌───────────────┐                                │
│  │  llm_client   │──▶ Anthropic API / Ollama      │
│  └──────┬────────┘                                │
│         │ result (DB に保存)                       │
│         ▼                                         │
│  ┌───────────────────────┐                        │
│  │ suggestion_viewer     │ (別プロセス・tkinter)   │
│  └───────────────────────┘                        │
└──────────────────────────────────────────────────────┘
```

---

## ファイル構成

```
AISupportSuggest/
├── main.py                      # エントリポイント（OS判定→UIアプリ起動）
├── src/
│   ├── config.py                # 設定値一元管理
│   ├── database.py              # SQLite CRUD
│   ├── event_detector.py        # イベント駆動アクティビティ検出
│   ├── screenshot.py            # プラットフォーム別スクリーンショット
│   ├── llm_client.py            # Anthropic / Ollama クライアント
│   ├── prompts.py               # プロンプトテンプレート（semantic / optimization）
│   ├── analyzer.py              # 2段階分析オーケストレーション
│   └── ui/
│       ├── menubar_app.py       # macOS (rumps)
│       ├── tray_app_win.py      # Windows (pystray)
│       └── suggestion_viewer.py # 結果表示（別プロセス）
├── data/                        # 自動生成・.gitignore対象
│   ├── activity.db
│   └── screenshots/
├── requirements.txt
├── setup.sh / setup.bat
└── TECH.md
```

---

## イベント駆動型ログ（ML観点の設計）

### 旧方式（v0.1）との比較

| | 旧: 定時ポーリング | 新: イベント駆動 |
|---|---|---|
| 記録方式 | 5分ごとにスナップショット | 状態変化時のみ記録 |
| 持続時間 | なし（推定5分） | 正確な秒数 |
| データ量 | 冗長（同じアプリが繰り返し記録） | 効率的（変化時のみ） |
| 短い操作 | 5分以内の操作は欠落 | 1秒単位で検出 |
| idle検出 | なし | 5分間変化なし→idle_start |

### イベントタイプ

| event_type | 発生条件 |
|---|---|
| `app_switch` | アクティブアプリが変わった |
| `window_change` | 同アプリ内でウィンドウタイトルが変わった |
| `idle_start` | 5分間（`IDLE_THRESHOLD_SECONDS`）変化なし |
| `idle_end` | idle状態から復帰 |

### ML/分析で抽出可能な特徴量

- **アプリ使用時間分布**: 各アプリの合計 `duration_seconds`
- **コンテキストスイッチ頻度**: 単位時間あたりの `app_switch` 数
- **遷移パターン**: アプリ A → B の遷移確率（マルコフ連鎖）
- **集中度指標**: 連続使用時間の中央値・最大値
- **時間帯別パターン**: 午前/午後/夕方のアプリ構成の違い
- **idle比率**: 実作業時間 vs 離席時間

---

## データベーススキーマ

### `events` テーブル

```sql
CREATE TABLE events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,        -- ISO 8601
    event_type      TEXT    NOT NULL,        -- app_switch, window_change, idle_start, idle_end
    app_name        TEXT    NOT NULL,
    window_title    TEXT    DEFAULT '',
    screenshot_path TEXT,                    -- SCREENSHOT_MODE時のみ
    duration_seconds REAL,                   -- 次のイベントまでの持続時間
    created_at      TEXT    NOT NULL
);
```

### `daily_analysis` テーブル

```sql
CREATE TABLE daily_analysis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,        -- YYYY-MM-DD
    phase           TEXT    NOT NULL,        -- 'semantic' | 'optimization'
    event_count     INTEGER DEFAULT 0,
    app_summary     TEXT,                    -- JSON: {app: total_seconds}
    analysis_text   TEXT,                    -- LLMの分析結果全文
    created_at      TEXT    NOT NULL,
    UNIQUE(date, phase)
);
```

---

## 2段階分析パイプライン

### Phase 1: semantic（意味付け）

イベントログをLLMに渡し、各作業セッションの「意味」を推定する。

**入力例:**
```
14:00:05 → アプリ切替: Visual Studio Code - main.py (1395秒)
14:23:20   ウィンドウ変更: Visual Studio Code - config.py (102秒)
14:25:02 → アプリ切替: Chrome - Gmail (47秒)
14:25:49 → アプリ切替: Chrome - Google Drive (88秒)
14:27:17 → アプリ切替: Chrome - Gmail - 新規メール作成 (210秒)
```

**出力例:**
```
セッション1: 14:00〜14:23 — コード開発（main.py, config.py の編集）
セッション2: 14:23〜14:31 — メール作成のための資料収集
  → Gmail確認 → Google Driveで資料を探す → Gmailに戻ってメール作成
  推定: 「メールに添付する資料をDriveで探していた」
```

結果は `daily_analysis` テーブルに `phase='semantic'` で保存。

### Phase 2: optimization（ワークロード高速化提案）

Phase 1 の結果 + アプリ使用統計を入力に、5つの観点で改善提案を生成。

1. 自動化可能な繰り返し作業
2. AIで代替・補助できる作業
3. ツール統合による効率化
4. ワークフロー改善（作業順序・バッチ化等）
5. 具体的なツール・設定の推奨

結果は `daily_analysis` テーブルに `phase='optimization'` で保存。

---

## 設定値一覧（`src/config.py`）

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `USE_ANTHROPIC` | `True` | `False` で Ollama に切替 |
| `ANTHROPIC_API_KEY` | 環境変数 | Anthropic API キー |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama エンドポイント |
| `OLLAMA_MODEL` | `llama3.2` | テキスト用モデル |
| `OLLAMA_VISION_MODEL` | `llava` | 画像対応モデル |
| `POLL_INTERVAL_SECONDS` | `1` | ポーリング間隔（秒） |
| `IDLE_THRESHOLD_SECONDS` | `300` | idle判定閾値（秒） |
| `SCREENSHOT_MODE` | `False` | スクリーンショット撮影 |
| `SCREENSHOT_MAX_SEND` | `12` | 分析時に送る最大枚数 |
| `RECORD_ONLY` | `False` | 記録のみモード |
| `ANALYSIS_HOUR` | `0` | 分析実行時（0〜23） |
| `ANALYSIS_MINUTE` | `0` | 分析実行分 |

---

## 依存ライブラリ

| パッケージ | 用途 | プラットフォーム |
|-----------|------|----------------|
| `schedule` | 定期実行 | 共通 |
| `requests` | Ollama REST API | 共通 |
| `anthropic` | Anthropic API | 共通 |
| `rumps` | メニューバーアプリ | macOS |
| `pyobjc-framework-Cocoa` | macOS ネイティブ API | macOS |
| `pystray` | システムトレイ | Windows |
| `Pillow` | アイコン生成・スクリーンショット | Windows |
| `psutil` | プロセス情報取得 | Windows |

---

## 既知の制限

- **AppleScript の権限**: macOS のオートメーション許可が必要。なければ `Unknown`
- **スリープ中**: スレッド停止によりログは記録されない
- **DB ローテーション**: 自動なし。長期利用時は `data/activity.db` を手動管理
- **tkinter on macOS**: OS付属Pythonでは動作しない場合がある。Homebrew / pyenv の Python 3.11+ 推奨
