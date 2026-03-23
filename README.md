# AISupportSuggest

1日の作業を自動記録し、AIが「もっと楽にできる方法」を毎晩提案してくれる macOS メニューバーアプリ。

---

## 概要

- **5分ごと**にアクティブなアプリ名・ウィンドウタイトルを記録
- **毎日0時**に1日分の作業ログをローカルLLM（Ollama）で分析
- **ポップアップウィンドウ**で省力化・自動化の提案を表示
- データはすべてローカル処理 — 外部送信なし（Ollamaモード時）

```
┌─────────────────────────────────┐
│   AI省力化提案                   │
│                                 │
│ 【メール定型文の自動生成】        │
│ ・現在の作業: メール作成に30分    │
│ ・AI活用法: テンプレ＋LLMで文案  │
│ ・使えるツール: Ollama / Claude  │
│ ・期待効果: 作業時間を80%削減    │
│                                 │
│           [ 閉じる ]            │
└─────────────────────────────────┘
```

---

## 必要環境

- macOS 12以降
- Python 3.11以降
- [Ollama](https://ollama.com)（ローカルLLM実行環境）

---

## セットアップ

### 1. Ollama のインストール

[https://ollama.com](https://ollama.com) からダウンロードしてインストール。

```bash
# モデルをダウンロード（初回のみ・約2GB）
ollama pull llama3.2
```

### 2. パッケージのインストール

```bash
cd ~/Development/AISupportSuggest
bash setup.sh
```

または手動で:

```bash
pip3 install -r requirements.txt
```

### 3. macOS のプライバシー許可

初回起動時に以下の許可ダイアログが表示されます。いずれも「許可する」を選択してください。

| 権限 | 用途 |
|------|------|
| オートメーション | アクティブなアプリ名・ウィンドウタイトルの取得 |

システム設定 → プライバシーとセキュリティ → オートメーション から手動で許可することもできます。

---

## 起動方法

```bash
# ターミナル1: Ollama を起動
ollama serve

# ターミナル2: アプリを起動
python3 main.py
```

起動するとメニューバーに `AI` と表示されます。

---

## 使い方

### メニューバーのメニュー

| メニュー項目 | 動作 |
|---|---|
| 今日のログ件数を確認 | 今日の記録件数を表示 |
| 今すぐ分析する | すぐに分析して提案を表示 |
| 終了 | アプリを終了 |

### 自動実行

- **5分ごと**: バックグラウンドでアクティブアプリを自動記録
- **毎日0:00**: 1日分のログを分析し、提案ウィンドウを自動表示

---

## 設定

`config.py` を編集してカスタマイズできます。

```python
# 使用するOllamaモデル
OLLAMA_MODEL = "llama3.2"        # 軽量・高速
# OLLAMA_MODEL = "gemma3:12b"    # 高品質（要16GB RAM）

# 分析を実行する時刻
ANALYSIS_HOUR   = 0   # 0時
ANALYSIS_MINUTE = 0

# アクティビティの記録間隔（分）
LOG_INTERVAL_MINUTES = 5
```

### Anthropic API（Claude）に切り替える場合

```python
# config.py
USE_ANTHROPIC = True
```

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 main.py
```

---

## ファイル構成

```
AISupportSuggest/
├── main.py               # エントリーポイント
├── menubar_app.py        # メニューバーアプリ本体
├── activity_logger.py    # アクティビティ記録
├── analyzer.py           # LLMプロンプト生成・分析実行
├── llm_client.py         # Ollama / Anthropic クライアント
├── suggestion_viewer.py  # 提案表示ウィンドウ
├── config.py             # 設定
├── requirements.txt
├── setup.sh
└── data/
    └── activity_log.jsonl  # 作業ログ（自動生成）
```

---

## ログのプライバシー

- 記録されるのは**アプリ名とウィンドウタイトルのみ**（スクリーンショットなし）
- ログは `data/activity_log.jsonl` にローカル保存
- Ollamaモード時はすべての処理がローカル完結 — データは外部送信されません
- ログを削除したい場合: `data/activity_log.jsonl` を削除してください

---

## トラブルシューティング

**「Ollama に接続できません」と表示される**
```bash
ollama serve   # Ollama を起動してから再試行
```

**アプリ名が「Unknown」になる**
→ システム設定 → プライバシーとセキュリティ → オートメーション で本アプリの許可を確認してください。

**モデルが遅い / 重い**
```bash
ollama pull llama3.2   # 軽量モデルに切り替え
# config.py の OLLAMA_MODEL = "llama3.2" を確認
```
