import json
import subprocess
import threading
import time
from datetime import datetime

from config import ACTIVITY_LOG_FILE, LOG_INTERVAL_MINUTES


def get_active_app_info() -> tuple[str, str]:
    """AppleScript でフロントウィンドウのアプリ名とタイトルを取得する。"""
    script = """
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        set frontWindow to ""
        try
            set frontWindow to name of first window of (first application process whose frontmost is true)
        end try
        return frontApp & "|||" & frontWindow
    end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|||")
            app_name = parts[0].strip() if len(parts) > 0 else "Unknown"
            window_title = parts[1].strip() if len(parts) > 1 else ""
            return app_name, window_title
    except Exception:
        pass
    return "Unknown", ""


def log_activity() -> dict:
    """現在のアクティブアプリをログファイルに追記する。"""
    app_name, window_title = get_active_app_info()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "app": app_name,
        "window": window_title,
    }
    with open(ACTIVITY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def get_today_log() -> list[dict]:
    """今日分のログエントリを返す。"""
    today = datetime.now().date().isoformat()
    entries = []
    if not ACTIVITY_LOG_FILE.exists():
        return entries
    with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("timestamp", "").startswith(today):
                    entries.append(entry)
            except json.JSONDecodeError:
                pass
    return entries


class ActivityLogger:
    """バックグラウンドスレッドで定期的にアクティビティを記録する。"""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="ActivityLogger")
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                log_activity()
            except Exception:
                pass
            self._stop_event.wait(LOG_INTERVAL_MINUTES * 60)
