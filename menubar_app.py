import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import rumps
import schedule

from activity_logger import ActivityLogger, get_today_log
from analyzer import analyze_today
from config import ANALYSIS_HOUR, ANALYSIS_MINUTE, RECORD_ONLY

VIEWER_SCRIPT = Path(__file__).parent / "suggestion_viewer.py"


class AISupportApp(rumps.App):
    def __init__(self):
        icon = "録" if RECORD_ONLY else "AI"
        super().__init__(icon, quit_button=None)
        self._logger = ActivityLogger()
        analyze_label = "今日のログを確認する" if RECORD_ONLY else "今すぐ分析する"
        self.menu = [
            rumps.MenuItem("今日のログ件数を確認", callback=self.show_log_count),
            rumps.MenuItem(analyze_label, callback=self.run_analysis_now),
            None,
            rumps.MenuItem("終了", callback=self.quit_app),
        ]
        self._logger.start()
        self._start_scheduler()

    # ── スケジューラー ──────────────────────────────────────

    def _start_scheduler(self):
        schedule.every().day.at(
            f"{ANALYSIS_HOUR:02d}:{ANALYSIS_MINUTE:02d}"
        ).do(self._scheduled_analysis)

        t = threading.Thread(target=self._scheduler_loop, daemon=True, name="Scheduler")
        t.start()

    def _scheduler_loop(self):
        while True:
            schedule.run_pending()
            time.sleep(30)

    def _scheduled_analysis(self):
        self._run_analysis_async()

    # ── 分析の実行 ──────────────────────────────────────────

    def _run_analysis_async(self):
        def _run():
            try:
                result = analyze_today()
                self._open_viewer(result)
            except Exception as e:
                rumps.alert(title="エラーが発生しました", message=str(e))

        threading.Thread(target=_run, daemon=True, name="Analyzer").start()

    def _open_viewer(self, text: str):
        """提案テキストを一時ファイルに書き出し、別プロセスで表示する。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write(text)
            tmp_path = f.name

        subprocess.Popen(
            [sys.executable, str(VIEWER_SCRIPT), tmp_path],
            close_fds=True,
        )

    # ── メニュー操作 ─────────────────────────────────────────

    @rumps.clicked("今日のログ件数を確認")
    def show_log_count(self, _):
        entries = get_today_log()
        n = len(entries)
        rumps.alert(
            title="今日の活動ログ",
            message=f"記録件数: {n} 件（約 {n * 5} 分分のデータ）",
        )

    @rumps.clicked("今すぐ分析する")
    def run_analysis_now(self, _):
        self._run_analysis_async()

    def quit_app(self, _):
        self._logger.stop()
        rumps.quit_application()
