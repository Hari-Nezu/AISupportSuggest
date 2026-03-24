"""macOS メニューバーアプリ（rumps 使用）。"""
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import rumps
import schedule

from src.analyzer import analyze_today
from src.config import ANALYSIS_HOUR, ANALYSIS_MINUTE, RECORD_ONLY
from src.database import Database
from src.event_detector import EventDetector

_VIEWER_BINARY = Path(__file__).resolve().parents[2] / "bin" / "SuggestionViewer"
_VIEWER_SCRIPT = Path(__file__).resolve().parent / "suggestion_viewer.py"


class AISupportApp(rumps.App):
    def __init__(self):
        icon_text = "録" if RECORD_ONLY else "AI"
        super().__init__(icon_text, quit_button=None)

        self._db = Database()
        self._detector = EventDetector(self._db)

        analyze_label = "今日のログを確認する" if RECORD_ONLY else "今すぐ分析する"
        self.menu = [
            rumps.MenuItem("作業開始", callback=self.task_start),
            rumps.MenuItem("作業終了", callback=self.task_end),
            None,
            rumps.MenuItem("今日のログ件数を確認", callback=self.show_log_count),
            rumps.MenuItem(analyze_label, callback=self.run_analysis_now),
            None,
            rumps.MenuItem("終了", callback=self.quit_app),
        ]

        self._detector.start()
        self._start_scheduler()

    # ── スケジューラー ────────────────────────────────────────────────

    def _start_scheduler(self):
        schedule.every().day.at(
            f"{ANALYSIS_HOUR:02d}:{ANALYSIS_MINUTE:02d}"
        ).do(self._run_analysis_async)
        t = threading.Thread(target=self._scheduler_loop, daemon=True, name="Scheduler")
        t.start()

    def _scheduler_loop(self):
        while True:
            schedule.run_pending()
            time.sleep(30)

    # ── 分析 ──────────────────────────────────────────────────────────

    def _run_analysis_async(self):
        def _run():
            try:
                result = analyze_today(self._db)
                self._open_viewer(result)
                rumps.notification(
                    title="AI省力化提案",
                    subtitle="今日の提案が届きました",
                    message="クリックして確認してください",
                )
            except Exception as e:
                rumps.alert(title="エラー", message=str(e))

        threading.Thread(target=_run, daemon=True, name="Analyzer").start()

    def _open_viewer(self, text: str):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False,
        ) as f:
            f.write(text)
            tmp_path = f.name
        if _VIEWER_BINARY.exists():
            subprocess.Popen([str(_VIEWER_BINARY), tmp_path])
        else:
            subprocess.Popen([sys.executable, str(_VIEWER_SCRIPT), tmp_path])

    # ── メニューコールバック ──────────────────────────────────────────

    @rumps.clicked("作業開始")
    def task_start(self, _):
        self._db.insert_task_event("task_start")
        rumps.notification(title="作業開始", subtitle="", message="タスク開始を記録しました")

    @rumps.clicked("作業終了")
    def task_end(self, _):
        self._db.insert_task_event("task_end")
        rumps.notification(title="作業終了", subtitle="", message="タスク終了を記録しました")

    @rumps.clicked("今日のログ件数を確認")
    def show_log_count(self, _):
        n = self._db.get_today_event_count()
        rumps.alert(
            title="今日の活動ログ",
            message=f"イベント数: {n} 件",
        )

    @rumps.clicked("今すぐ分析する")
    @rumps.clicked("今日のログを確認する")
    def run_analysis_now(self, _):
        self._run_analysis_async()

    def quit_app(self, _):
        self._detector.stop()
        rumps.quit_application()
