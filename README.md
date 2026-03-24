# AISupportSuggest

![version](https://img.shields.io/badge/version-0.2.0-blue)

1日の作業をイベント単位で自動記録し、AIが作業の「意味」を読み取って効率化を提案してくれるアプリ。
macOS / Windows 対応。

> 詳細な技術仕様は [docs/TECH.md](./docs/TECH.md) を参照してください。

---

## こんな人に

- 毎日同じような作業を繰り返している
- AIを活用したいけど、何から始めればいいかわからない
- 業務効率化のヒントが欲しい

---

## 動作イメージ

毎日0時に、その日の作業を **2段階** で分析します。

```
Phase 1: 意味付け
  「14:00〜14:25 VSCode で main.py を編集」
  「14:25〜14:30 Chrome で Gmail → Google Drive → Gmail」
   → 推定: 「メールに添付する資料を Google Drive で探していた」

Phase 2: 高速化提案
  「Drive → Gmail の繰り返しが多い → Drive の共有リンクを活用すれば
   ダウンロード→添付の手間が省ける」
```

---

## 必要環境

| | macOS | Windows |
|---|---|---|
| OS | macOS 12 以降 | Windows 10 / 11 |
| Python | 3.11 以降 | 3.11 以降 |
| 共通 | Anthropic API キー（会社から発行されたもの） ||

---

## セットアップ

### 1. API キーを設定する

**macOS:**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-ここにキーを貼り付け"' >> ~/.zshrc
source ~/.zshrc
echo $ANTHROPIC_API_KEY   # 確認
```

**Windows:**
1. Windowsキー →「環境変数」で検索
2.「システム環境変数の編集」→「環境変数」
3. ユーザー環境変数に `ANTHROPIC_API_KEY` を追加

または PowerShell で一時設定:
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-ここにキーを貼り付け"
```

### 2. アプリのセットアップ

**macOS:**
```bash
cd AISupportSuggest
bash scripts/setup.sh
```

**Windows:**
```bat
cd AISupportSuggest
scripts\setup.bat
```

### 3. プライバシー許可（macOS のみ）

初回起動時に許可ダイアログが表示されます。

| 権限 | 用途 |
|------|------|
| オートメーション | アクティブなアプリ名・ウィンドウタイトルの取得 |
| 入力監視 | キーボードショートカットの種別検出（内容は記録しません） |

---

## 起動方法

**macOS:**
```bash
python3 main.py
```

**Windows:**
```bat
python main.py
```

メニューバー（macOS）/ システムトレイ（Windows）に `AI` が表示されたら起動完了です。

---

## 使い方

| メニュー | 動作 |
|---|---|
| 今日のログ件数を確認 | 今日記録されたイベント数を表示 |
| 今すぐ分析する | その場で Phase 1 + Phase 2 を実行 |
| 終了 | アプリを終了 |

自動では **毎日0時** に分析が実行されます。

---

## データの記録方式

旧バージョンの5分間隔ポーリングから **イベント駆動型** に変更されました。

- アプリ切り替え・ウィンドウ変更が発生した瞬間だけ記録
- 各イベントに持続時間（秒）が付与される
- 5分間変化がないと idle（離席）として記録
- データは SQLite（`data/activity.db`）に保存

---

## オプション機能

### 収録のみモード

LLM API を一切呼ばず、記録だけを行うモード。

`src/config.py` を編集:
```python
RECORD_ONLY = True
```

アイコンが `録` に変わります。

### ローカル LLM（Ollama）への切り替え

[Ollama](https://ollama.com) をインストール後、`src/config.py` を編集:
```python
USE_ANTHROPIC = False
OLLAMA_MODEL  = "llama3.2"
```

```bash
ollama serve
python3 main.py
```

---

## プロジェクト構造

```
AISupportSuggest/
├── main.py                      # エントリポイント
├── src/
│   ├── config.py                # 設定
│   ├── database.py              # SQLite DB
│   ├── event_detector.py        # イベント駆動ログ
│   ├── llm_client.py            # LLM バックエンド
│   ├── prompts.py               # プロンプトテンプレート
│   ├── analyzer.py              # 2段階分析
│   └── ui/
│       ├── menubar_app.py           # macOS (rumps)
│       ├── tray_app_win.py          # Windows (pystray)
│       ├── SuggestionViewer.swift   # 結果表示ウィンドウ (macOS ネイティブ)
│       └── suggestion_viewer.py     # 結果表示フォールバック (Python)
├── data/                        # 自動生成（.gitignore）
│   └── activity.db              # イベント DB
├── requirements.txt
├── scripts/
│   ├── setup.sh
│   └── setup.bat
└── docs/
    └── TECH.md
```

---

## プライバシーについて

- **アプリ名とウィンドウタイトルのみ** を記録（画面キャプチャなし）
- Anthropic API の商用利用では、入出力データはモデル学習に使用されません
- ログは `data/activity.db` にローカル保存。削除したい場合はこのファイルを削除

> **お願い**: 自分自身の業務改善のために使うことを想定しています。
> 他者への監視目的には使わないでください。

---

## トラブルシューティング

**「ANTHROPIC_API_KEY が設定されていません」と表示される**
```bash
echo $ANTHROPIC_API_KEY
source ~/.zshrc
```

**アプリ名が「Unknown」になる**

macOS: システム設定 → プライバシーとセキュリティ → オートメーション で許可を確認。

**分析結果を確認したい**

DB を直接参照できます:
```bash
sqlite3 data/activity.db "SELECT date, phase, analysis_text FROM daily_analysis ORDER BY date DESC LIMIT 5;"
```
