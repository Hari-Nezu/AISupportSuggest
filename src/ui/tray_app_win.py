"""Windows 用システムトレイアプリ（pystray 使用）。"""
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import schedule
import pystray
from PIL import Image, ImageDraw, ImageFont

from src.analyzer import analyze_today
from src.config import ANALYSIS_HOUR, ANALYSIS_MINUTE, RECORD_ONLY
from src.database import Database
from src.event_detector import EventDetector
from src.shortcut_detector import ShortcutDetector

VIEWER_SCRIPT = Path(__file__).resolve().parent / "suggestion_viewer.py"


def _create_icon_image(text: str = "AI") -> Image.Image:
    img = Image.new("RGB", (64, 64), color="#1e1e2e")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (64 - (bbox[2] - bbox[0])) // 2
    y = (64 - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, fill="#89b4fa", font=font)
    return img


def _show_message(title: str, message: str):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


class WinTrayApp:
    def __init__(self):
        self._db = Database()
        self._detector = EventDetector(self._db)
        self._shortcut_detector = ShortcutDetector(self._db)
        icon_text = "録" if RECORD_ONLY else "AI"
        analyze_label = "今日のログを確認する" if RECORD_ONLY else "今すぐ分析する"

        menu = pystray.Menu(
            pystray.MenuItem("直前の作業にフラグ", self._flag_frustration),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("今日のログ件数を確認", self._show_log_count),
            pystray.MenuItem(analyze_label, self._run_analysis_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self._quit),
        )
        self._icon = pystray.Icon(
            "AISupportSuggest",
            _create_icon_image(icon_text),
            "AISupportSuggest",
            menu,
        )

    def run(self):
        self._detector.start()
        self._shortcut_detector.start()
        self._start_scheduler()
        self._icon.run()

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

    def _run_analysis_async(self):
        def _run():
            try:
                result = analyze_today(self._db)
                self._open_viewer(result)
            except Exception as e:
                _show_message("エラー", str(e))

        threading.Thread(target=_run, daemon=True, name="Analyzer").start()

    def _open_viewer(self, text: str):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False,
        ) as f:
            f.write(text)
            tmp_path = f.name
        subprocess.Popen([sys.executable, str(VIEWER_SCRIPT), tmp_path], close_fds=True)

    def _flag_frustration(self, icon, item):
        from datetime import datetime
        today = datetime.now().date().isoformat()
        if self._db.flag_latest_task_frustration(today):
            _show_message("フラグを記録", "直前の作業にフラグを立てました")
        else:
            _show_message("タスクが見つかりません", "先に「今すぐ分析する」を実行してください")

    def _show_log_count(self, icon, item):
        n = self._db.get_today_event_count()
        _show_message("今日の活動ログ", f"イベント数: {n} 件")

    def _run_analysis_now(self, icon, item):
        self._run_analysis_async()

    def _quit(self, icon, item):
        self._detector.stop()
        self._shortcut_detector.stop()
        icon.stop()
