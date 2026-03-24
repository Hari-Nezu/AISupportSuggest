"""
イベント駆動型アクティビティ検出。

定期ポーリング（1秒間隔）でアクティブウィンドウを監視し、
状態が変わった時だけ DB にイベントを記録する。
各イベントには前のイベントからの持続時間が付与される。
"""
import platform
import subprocess
import threading
from datetime import datetime

from src.config import (
    IDLE_THRESHOLD_SECONDS,
    POLL_INTERVAL_SECONDS,
    SCREENSHOT_MODE,
)
from src.database import Database
from src.screenshot import capture_screenshot

PLATFORM = platform.system()


# ── プラットフォーム別アクティブウィンドウ取得 ─────────────────────────────────

def _get_active_app_macos() -> tuple[str, str]:
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
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|||")
            app = parts[0].strip() if len(parts) > 0 else "Unknown"
            win = parts[1].strip() if len(parts) > 1 else ""
            return app, win
    except Exception:
        pass
    return "Unknown", ""


def _get_active_app_windows() -> tuple[str, str]:
    try:
        import ctypes
        import ctypes.wintypes
        import psutil

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        window_title = buff.value

        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = psutil.Process(pid.value)
        app_name = process.name().removesuffix(".exe")

        return app_name, window_title
    except Exception:
        pass
    return "Unknown", ""


def get_active_app_info() -> tuple[str, str]:
    if PLATFORM == "Windows":
        return _get_active_app_windows()
    return _get_active_app_macos()


# ── イベント検出器 ────────────────────────────────────────────────────────────

class EventDetector:
    """
    アクティブウィンドウの変化を検出し、DB にイベントを記録する。

    記録される情報:
    - event_type: 'app_switch' | 'window_change' | 'idle_start' | 'idle_end'
    - app_name / window_title
    - duration_seconds: 前の状態の持続時間
    - screenshot_path: (SCREENSHOT_MODE 時のみ)
    """

    def __init__(self, db: Database | None = None):
        self._db = db or Database()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # 現在の状態
        self._current_app: str | None = None
        self._current_window: str | None = None
        self._state_start: datetime | None = None
        self._last_event_id: int | None = None

        # idle 検出用
        self._idle = False
        self._no_change_seconds = 0.0

    def start(self):
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="EventDetector",
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        # 最後のイベントの duration を確定させる
        self._close_current_event()

    @property
    def db(self) -> Database:
        return self._db

    # ── メインループ ──────────────────────────────────────────────────────

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                pass
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def _tick(self):
        app, window = get_active_app_info()
        now = datetime.now()

        # 状態が変わったか判定
        app_changed = app != self._current_app
        window_changed = window != self._current_window

        if not app_changed and not window_changed:
            # 状態変化なし → idle チェック
            self._no_change_seconds += POLL_INTERVAL_SECONDS
            if (
                not self._idle
                and self._no_change_seconds >= IDLE_THRESHOLD_SECONDS
            ):
                self._idle = True
                self._close_current_event()
                self._last_event_id = self._db.insert_event(
                    timestamp=now.isoformat(),
                    event_type="idle_start",
                    app_name=app,
                    window_title=window,
                )
                self._state_start = now
            return

        # idle から復帰
        if self._idle:
            self._idle = False
            self._close_current_event()
            self._db.insert_event(
                timestamp=now.isoformat(),
                event_type="idle_end",
                app_name=app,
                window_title=window,
            )

        self._no_change_seconds = 0.0

        # 前のイベントを閉じる（duration 確定）
        self._close_current_event()

        # 新しいイベントを記録
        event_type = "app_switch" if app_changed else "window_change"
        screenshot_path = None
        if SCREENSHOT_MODE and app_changed:
            screenshot_path = capture_screenshot(now.isoformat())

        self._last_event_id = self._db.insert_event(
            timestamp=now.isoformat(),
            event_type=event_type,
            app_name=app,
            window_title=window,
            screenshot_path=screenshot_path,
        )
        self._current_app = app
        self._current_window = window
        self._state_start = now

    def _close_current_event(self):
        """直前のイベントに duration を書き込む。"""
        if self._last_event_id and self._state_start:
            duration = (datetime.now() - self._state_start).total_seconds()
            self._db.update_event_duration(self._last_event_id, duration)
            self._last_event_id = None
            self._state_start = None
