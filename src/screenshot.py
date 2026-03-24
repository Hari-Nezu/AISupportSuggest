"""プラットフォーム別スクリーンショット撮影。"""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from src.config import SCREENSHOT_DIR

PLATFORM = platform.system()


def _capture_macos(filepath: Path) -> bool:
    try:
        r = subprocess.run(
            ["screencapture", "-x", "-t", "png", str(filepath)],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0 and filepath.exists()
    except Exception:
        return False


def _capture_windows(filepath: Path) -> bool:
    try:
        from PIL import ImageGrab
        ImageGrab.grab().save(str(filepath), "PNG")
        return filepath.exists()
    except Exception:
        return False


def capture_screenshot(timestamp_iso: str) -> str | None:
    """スクリーンショットを撮影して保存パスを返す。失敗時 None。"""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    safe_ts = timestamp_iso.replace(":", "-")
    filepath = SCREENSHOT_DIR / f"{safe_ts}.png"

    ok = _capture_windows(filepath) if PLATFORM == "Windows" else _capture_macos(filepath)
    return str(filepath) if ok else None
