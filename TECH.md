# TECH.md — 技術仕様

> 利用者向けのセットアップ手順は [README.md](./README.md) を参照してください。

---

## アーキテクチャ概要

```
┌──────────────────────────────────────────────┐
│  macOS プロセス                               │
│                                              │
│  ┌─────────────┐   5分ごと   ┌────────────┐ │
│  │ menubar_app │ ──────────▶ │activity_   │ │
│  │  (rumps)    │             │logger      │ │
│  └──────┬──────┘             └─────┬──────┘ │
│         │ 0:00 / 手動              │ append │
│         ▼                          ▼        │
│  ┌─────────────┐        data/activity_log   │
│  │  analyzer   │◀────────── .jsonl          │
│  └──────┬──────┘                            │
│         │ prompt                            │
│         ▼                                   │
│  ┌─────────────┐                            │
│  │  llm_client │──▶ Ollama (localhost:11434)│
│  └──────┬──────┘    または Anthropic API    │
│         │ result                            │
│         ▼                                   │
│  ┌─────────────────┐                        │
│  │suggestion_viewer│ (別サブプロセス・tkinter)│
│  └─────────────────┘                        │
└──────────────────────────────────────────────┘
```

---

## ファイル構成

```
AISupportSuggest/
├── main.py               # エントリーポイント
├── menubar_app.py        # rumps メニューバーアプリ・スケジューラー
├── activity_logger.py    # AppleScript によるアクティビティ記録
├── analyzer.py           # ログ集計・LLMプロンプト生成・分析実行
├── llm_client.py         # Ollama / Anthropic クライアント
├── suggestion_viewer.py  # 提案表示ウィンドウ（サブプロセス起動）
├── config.py             # 設定値
├── requirements.txt
├── setup.sh
└── data/
    └── activity_log.jsonl  # 作業ログ（自動生成・JSONL形式）
```

---

## モジュール詳細

### `config.py`

全モジュールが参照する設定値を一元管理。

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API エンドポイント |
| `OLLAMA_MODEL` | `llama3.2` | 使用するモデル名 |
| `USE_ANTHROPIC` | `False` | `True` にすると Anthropic API を使用 |
| `ANTHROPIC_API_KEY` | 環境変数から取得 | Anthropic API キー |
| `LOG_INTERVAL_MINUTES` | `5` | アクティビティ記録間隔（分） |
| `ANALYSIS_HOUR` | `0` | 自動分析を実行する時（0〜23） |
| `ANALYSIS_MINUTE` | `0` | 自動分析を実行する分 |

---

### `activity_logger.py`

**`get_active_app_info() -> (app_name, window_title)`**

AppleScript を `osascript` 経由で実行し、フロントウィンドウのアプリ名とタイトルを取得する。タイムアウトは5秒。

```applescript
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
    set frontWindow to name of first window of ...
end tell
```

**`log_activity()`**

`get_active_app_info()` を呼び出し、以下の形式で `activity_log.jsonl` に追記する。

```json
{"timestamp": "2026-03-23T14:05:00", "app": "Finder", "window": "書類"}
```

**`ActivityLogger`**

デーモンスレッドで `log_activity()` を `LOG_INTERVAL_MINUTES` 間隔で呼び出すクラス。`start()` / `stop()` で制御する。

---

### `llm_client.py`

**`query_ollama(prompt, model=None) -> str`**

`POST /api/generate` にリクエスト。`stream: false` でレスポンスを一括取得。タイムアウトは180秒。

**`query_anthropic(prompt) -> str`**

`anthropic` SDK 経由で `claude-sonnet-4-6` モデルを呼び出す。`USE_ANTHROPIC=True` かつ `ANTHROPIC_API_KEY` が設定されている場合に使用される。

**`query_llm(prompt) -> str`**

`USE_ANTHROPIC` フラグで上記2つを切り替えるエントリ関数。

**`list_ollama_models() -> list[str]`**

`GET /api/tags` でインストール済みモデル一覧を返す。

---

### `analyzer.py`

**`build_prompt(entries) -> str`**

ログエントリをアプリ名で集計し、使用時間（エントリ数 × 5分）とウィンドウタイトルをまとめてプロンプトを生成する。

集計例:
```
- Xcode（約90分）: MyApp.xcodeproj、ContentView.swift
- Mail（約30分）: 受信トレイ
```

**`analyze_today() -> str`**

今日分のログを取得 → プロンプト生成 → `query_llm()` に渡して結果を返す。

---

### `menubar_app.py`

`rumps.App` を継承した `AISupportApp` クラス。

- **メインスレッド**: `rumps` のイベントループ
- **ActivityLogger スレッド**: デーモンスレッドで常時記録
- **Scheduler スレッド**: `schedule` ライブラリで30秒ごとに `run_pending()` を実行
- **Analyzer スレッド**: 分析実行時に都度生成（UIをブロックしない）

`_open_viewer(text)` は結果を一時ファイルに書き出し、`suggestion_viewer.py` を `subprocess.Popen` で起動することで、メインスレッドと tkinter の競合を回避している。

---

### `suggestion_viewer.py`

単独の Python プロセスとして起動される。起動引数にテキストファイルのパスを受け取り、`tkinter.scrolledtext` で表示する。

```bash
python3 suggestion_viewer.py /tmp/xxxxxxxx.txt
```

メインプロセスとは完全に分離しているため、tkinter の GIL・メインスレッド制約の影響を受けない。

---

## データフォーマット

### `data/activity_log.jsonl`

1行1エントリの JSONL 形式。

```jsonl
{"timestamp": "2026-03-23T09:00:00", "app": "Safari", "window": "GitHub - AISupportSuggest"}
{"timestamp": "2026-03-23T09:05:00", "app": "Visual Studio Code", "window": "menubar_app.py"}
{"timestamp": "2026-03-23T09:10:00", "app": "Mail", "window": "受信トレイ (3)"}
```

今日分のエントリは `timestamp` の先頭10文字（日付部分）で絞り込む。

---

## LLMバックエンドの切り替え

### Ollama（デフォルト）

```python
# config.py
USE_ANTHROPIC = False
OLLAMA_MODEL  = "llama3.2"
```

推奨モデル:

| モデル | RAM目安 | 特徴 |
|--------|---------|------|
| `llama3.2` | 4GB | 軽量・高速 |
| `gemma3:12b` | 16GB | 高品質 |
| `mistral` | 8GB | バランス型 |

### Anthropic API（Claude）

```python
# config.py
USE_ANTHROPIC = True
```

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 main.py
```

使用モデル: `claude-sonnet-4-6`（`llm_client.py` の `query_anthropic()` 内で指定）

---

## 依存ライブラリ

| パッケージ | 用途 |
|-----------|------|
| `rumps` | macOS メニューバーアプリフレームワーク |
| `schedule` | 定期実行スケジューラー |
| `requests` | Ollama REST API 呼び出し |
| `pyobjc-framework-Cocoa` | macOS ネイティブ API（rumps 依存） |
| `anthropic` | Anthropic API クライアント（オプション） |

---

## 既知の制限・注意点

- **AppleScript の権限**: macOS のオートメーション許可が必要。許可がないとアプリ名が `Unknown` になる
- **スリープ中の記録**: Mac がスリープ中はスレッドが停止するためログは記録されない
- **ログのローテーション**: 現在は自動ローテーションなし。長期利用時は `data/activity_log.jsonl` を手動で削除・アーカイブすること
- **tkinter on macOS**: macOS 付属の Python では tkinter が正常動作しない場合がある。`brew install python` または pyenv 経由の Python 3.11+ を推奨
