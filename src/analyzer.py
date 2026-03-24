"""
分析オーケストレーション。

Phase 1 (semantic):      イベントログ → 作業の意味付け
Phase 2 (optimization):  意味付けデータ → ワークロード高速化提案

両 Phase の結果は daily_analysis テーブルに保存され、
翌日以降も参照できる。
"""
import json
from datetime import datetime

from src.config import RECORD_ONLY, SCREENSHOT_MAX_SEND, SCREENSHOT_MODE
from src.database import Database
from src.llm_client import query_llm, query_llm_with_images
from src.prompts import (
    build_optimization_prompt,
    build_semantic_prompt,
    format_app_summary,
    format_events_for_prompt,
)


def _format_record_only_summary(events: list[dict], app_summary: dict[str, float]) -> str:
    """RECORD_ONLY モードの場合のテキスト要約。"""
    lines = [
        f"## 記録モード — {datetime.now().strftime('%Y年%m月%d日')}",
        f"イベント数: {len(events)} 件",
        "",
        "### アプリ別使用時間",
        format_app_summary(app_summary),
        "",
        "### 直近のイベント（最新20件）",
        format_events_for_prompt(events[-20:]),
        "",
        "---",
        "※ RECORD_ONLY モードのため LLM 分析はスキップされました。",
        "  config.py で RECORD_ONLY = False に変更すると分析が有効になります。",
    ]
    return "\n".join(lines)


def analyze_today(db: Database | None = None) -> str:
    """
    今日のイベントログを分析して結果を返す。

    1. DB からイベント取得
    2. RECORD_ONLY なら要約のみ返す
    3. Phase 1: semantic（意味付け）→ DB に保存
    4. Phase 2: optimization（高速化提案）→ DB に保存
    5. 両結果を結合して返す
    """
    db = db or Database()
    today = datetime.now().date().isoformat()
    events = db.get_events_by_date(today)

    if not events:
        return (
            "今日のイベントログがありません。\n"
            "アプリを起動してしばらく操作すると、イベントが記録されます。"
        )

    app_summary = db.get_app_summary(today)

    # ── RECORD_ONLY モード ─────────────────────────────────────────────
    if RECORD_ONLY:
        return _format_record_only_summary(events, app_summary)

    # ── Phase 1: semantic（意味付け）───────────────────────────────────
    event_text = format_events_for_prompt(events)
    app_summary_text = format_app_summary(app_summary)

    has_screenshots = False
    screenshot_paths: list[str] = []
    if SCREENSHOT_MODE:
        screenshot_paths = db.get_screenshots_by_date(today, SCREENSHOT_MAX_SEND)
        has_screenshots = len(screenshot_paths) > 0

    semantic_prompt = build_semantic_prompt(today, event_text, has_screenshots)

    if has_screenshots:
        semantic_result = query_llm_with_images(semantic_prompt, screenshot_paths)
    else:
        semantic_result = query_llm(semantic_prompt)

    # DB に保存
    db.save_analysis(
        date_str=today,
        phase="semantic",
        analysis_text=semantic_result,
        event_count=len(events),
        app_summary=json.dumps(app_summary, ensure_ascii=False),
    )

    # ── Phase 2: optimization（高速化提案）─────────────────────────────
    optimization_prompt = build_optimization_prompt(today, semantic_result, app_summary_text)
    optimization_result = query_llm(optimization_prompt)

    # DB に保存
    db.save_analysis(
        date_str=today,
        phase="optimization",
        analysis_text=optimization_result,
        event_count=len(events),
        app_summary=json.dumps(app_summary, ensure_ascii=False),
    )

    # ── 結果を結合して返す ─────────────────────────────────────────────
    return (
        f"# {today} の分析結果\n\n"
        f"---\n\n"
        f"# Phase 1: 作業の意味付け\n\n"
        f"{semantic_result}\n\n"
        f"---\n\n"
        f"# Phase 2: ワークロード高速化提案\n\n"
        f"{optimization_result}"
    )
