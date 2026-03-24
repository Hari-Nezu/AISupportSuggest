"""
LLM プロンプトテンプレート。

Phase 1: semantic  — イベントログから作業の「意味付け」を行う
Phase 2: optimization — 意味付けデータからワークロード高速化を提案する
"""
from __future__ import annotations


def build_semantic_prompt(date_str: str, event_log_text: str) -> str:
    """
    Phase 1 プロンプト: 日付単位のイベントログを受け取り、
    各作業セッションの意味を推定して構造化する。

    例: 「Google Drive を開いた後に Gmail で新規メールを作成した」
        → 「ドキュメントを確認してメールに添付しようとしていた」
    """
    return f"""あなたはユーザーのPC作業パターンを分析する専門家です。
以下は {date_str} のイベントログです。各行は「アプリの切り替え」や「ウィンドウの変更」が
発生した瞬間を記録しています。

=== イベントログ ===
{event_log_text}
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
- 長時間のidle（離席・休憩と推定）

## [TASKS_JSON]

上記「作業セッション一覧」を以下の JSON 形式で出力してください。
時刻は HH:MM:SS 形式、label は日本語20字以内。
このブロックは必ず最後に出力してください。

```json
[
  {{"started_at": "HH:MM:SS", "ended_at": "HH:MM:SS", "label": "タスクの概要"}}
]
```"""


def build_optimization_prompt(date_str: str, semantic_text: str, app_summary_text: str) -> str:
    """
    Phase 2 プロンプト: 意味付けデータとアプリ使用統計から、
    ワークロードの高速化・省力化を提案する。
    """
    return f"""あなたは業務効率化の専門コンサルタントです。
以下は {date_str} のユーザーの作業分析データです。

=== アプリ使用時間 ===
{app_summary_text}

=== 作業の意味付け分析 ===
{semantic_text}
======================

この分析データをもとに、ユーザーのワークフローを高速化・省力化する提案を行ってください。
必ず日本語で回答し、以下の5つの観点から具体的に提案してください。

## 1. 自動化可能な繰り返し作業

今日のログで繰り返し発生していた操作パターンを特定し、
自動化する具体的な方法を提案してください。
（例: Zapier、Power Automate、シェルスクリプト、Python スクリプト等）

## 2. AIで代替・補助できる作業

LLM（Claude、ChatGPT等）やAIツールで高速化できる作業を特定してください。
- テキスト作成・要約・翻訳
- コードレビュー・生成
- データ整理・分析
- メール・メッセージのドラフト作成

## 3. ツール統合による効率化

複数アプリを行き来していた作業について、
ツールの統合や代替で効率化できるものを提案してください。
（例:「SlackとメールをSlackに統合」「SpreadsheetとNotionを統合」）

## 4. ワークフロー改善

作業順序の改善、バッチ処理化、時間帯の最適化など、
作業の進め方自体を改善する提案をしてください。
（例:「メール確認を1日3回にまとめる」「集中作業を午前に集約」）

## 5. 具体的なツール・設定の推奨

上記の提案を実現するための具体的なツール名、設定方法、
導入ステップを示してください。無料ツールを優先してください。

---

各提案は以下の形式で書いてください:

**【提案タイトル】**
- 現在の状況: （今日のログからの具体的な根拠）
- 改善案: （何をどうするか）
- 使えるツール: （具体名）
- 期待効果: （どれくらい時間短縮/省力化できるか）"""


def format_events_for_prompt(events: list[dict]) -> str:
    """イベントリストをプロンプト用のテキストに整形する。"""
    lines = []
    for e in events:
        ts = e.get("timestamp", "")
        # ISO形式から HH:MM:SS を抽出
        time_part = ts[11:19] if len(ts) >= 19 else ts
        etype = e.get("event_type", "")
        app = e.get("app_name", "")
        window = e.get("window_title", "")
        dur = e.get("duration_seconds")
        dur_str = f" ({dur:.0f}秒)" if dur else ""

        type_label = {
            "app_switch": "→ アプリ切替",
            "window_change": "  ウィンドウ変更",
            "idle_start": "⏸ idle開始",
            "idle_end": "▶ idle復帰",
            "shortcut":   "⌨ ショートカット",
        }.get(etype, etype)

        line = f"{time_part} {type_label}: {app}"
        if window:
            line += f" - {window}"
        line += dur_str
        lines.append(line)

    return "\n".join(lines)


def format_app_summary(app_summary: dict[str, float]) -> str:
    """アプリ別使用時間をプロンプト用テキストに整形する。"""
    lines = []
    for app, seconds in app_summary.items():
        minutes = seconds / 60
        if minutes >= 60:
            lines.append(f"- {app}: {minutes/60:.1f}時間")
        elif minutes >= 1:
            lines.append(f"- {app}: {minutes:.0f}分")
        else:
            lines.append(f"- {app}: {seconds:.0f}秒")
    return "\n".join(lines) if lines else "（データなし）"
