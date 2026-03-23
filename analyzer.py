from collections import Counter
from datetime import datetime

from activity_logger import get_today_log, get_today_screenshots
from config import SCREENSHOT_MAX_SEND, SCREENSHOT_MODE
from llm_client import query_llm, query_llm_with_images


def build_prompt(entries: list[dict], has_screenshots: bool = False) -> str:
    app_counter: Counter = Counter()
    app_windows: dict[str, set] = {}

    for entry in entries:
        app = entry.get("app", "Unknown")
        window = entry.get("window", "")
        app_counter[app] += 1
        app_windows.setdefault(app, set())
        if window:
            app_windows[app].add(window)

    lines = []
    for app, count in app_counter.most_common():
        minutes = count * 5
        windows = list(app_windows[app])[:5]
        windows_str = "、".join(windows) if windows else "（タイトル不明）"
        lines.append(f"- {app}（約{minutes}分）: {windows_str}")

    log_text = "\n".join(lines)
    date_str = datetime.now().strftime("%Y年%m月%d日")

    screenshot_note = (
        "\nまた、1日の作業画面のスクリーンショット（均等サンプリング）も添付します。"
        "画面の内容も参考にして、より具体的な提案をしてください。"
        if has_screenshots else ""
    )

    return f"""以下は{date_str}の1日のPC作業ログです（アプリ名・推定使用時間・ウィンドウタイトル）。{screenshot_note}

{log_text}

このユーザーの業務パターンを分析して、AIやLLMを活用することで省力化・自動化できる作業を3〜5つ提案してください。
各提案は以下の形式で日本語で書いてください：

【提案タイトル】
・現在の作業: （どんな作業をしているか）
・AI活用法: （具体的にどうAIを使うか）
・使えるツール: （Claude、Copilot、ChatGPT、ローカルLLM等）
・期待効果: （どれくらい省力化できるか）

ログに基づいて具体的かつ実践的な提案をしてください。"""


def analyze_today() -> str:
    entries = get_today_log()
    if not entries:
        return (
            "今日の活動ログがまだありません。\n\n"
            "アプリ起動後、5分ごとにアクティブなアプリが自動記録されます。\n"
            "しばらく経ってから再度「今すぐ分析」をお試しください。"
        )

    if SCREENSHOT_MODE:
        screenshot_paths = get_today_screenshots(entries, SCREENSHOT_MAX_SEND)
        if screenshot_paths:
            prompt = build_prompt(entries, has_screenshots=True)
            return query_llm_with_images(prompt, screenshot_paths)

    prompt = build_prompt(entries)
    return query_llm(prompt)
