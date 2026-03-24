"""
キーボードショートカット検出。

プライバシー方針:
- 記録するのは「ショートカットの種類（例: Cmd+S）」と「アプリ名」のみ
- キーストローク（実際に入力した文字）・クリップボード内容・ファイル名は一切記録しない
- 修飾キー（Cmd / Ctrl）を含むコンボのみを対象とし、通常の文字入力はスキップする

macOS: Input Monitoring 権限が必要
  システム設定 → プライバシーとセキュリティ → 入力監視 でターミナル／Python を許可

Windows: 特別な権限不要
"""
from __future__ import annotations

import platform
import time
import threading
from datetime import datetime

from src.database import Database
from src.event_detector import get_active_app_info

PLATFORM = platform.system()

try:
    from pynput import keyboard as _kb
    _PYNPUT_AVAILABLE = True
except ImportError:
    _PYNPUT_AVAILABLE = False

# 修飾キーのグループ
_CMD_KEYS  = {"cmd", "cmd_l", "cmd_r"}
_CTRL_KEYS = {"ctrl", "ctrl_l", "ctrl_r"}
_SHIFT_KEYS = {"shift", "shift_l", "shift_r"}
_ALT_KEYS  = {"alt", "alt_l", "alt_r", "alt_gr"}

# プラットフォームごとの主修飾キー
_PRIMARY_MOD = _CMD_KEYS if PLATFORM == "Darwin" else _CTRL_KEYS
_PRIMARY_LABEL = "Cmd" if PLATFORM == "Darwin" else "Ctrl"
_ALT_LABEL = "Opt" if PLATFORM == "Darwin" else "Alt"

# 連続記録を抑制するインターバル（秒）
_THROTTLE = 1.0


def _key_name(key) -> str:
    """pynput のキーオブジェクトを文字列に変換する。文字キーは大文字化。"""
    if hasattr(key, "char") and key.char:
        return key.char.upper()
    if hasattr(key, "name") and key.name:
        name = key.name
        # 修飾キー自体は呼び出し元でスキップ済みのはずだが念のため除外
        if any(name in g for g in (_CMD_KEYS, _CTRL_KEYS, _SHIFT_KEYS, _ALT_KEYS)):
            return ""
        return name.capitalize()
    return ""


class ShortcutDetector:
    """
    グローバルキーボードイベントを監視し、
    修飾キーを含むショートカットのみを DB に記録するクラス。
    """

    def __init__(self, db: Database):
        self._db = db
        self._modifiers: set[str] = set()
        self._last_recorded: dict[tuple[str, str], float] = {}
        self._listener = None
        self._lock = threading.Lock()

    # ── 公開インターフェース ──────────────────────────────────────────────

    def start(self):
        if not _PYNPUT_AVAILABLE:
            return
        try:
            self._listener = _kb.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()
        except Exception:
            # Input Monitoring 権限がない場合などはサイレントに無効化
            self._listener = None

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ── イベントハンドラ ──────────────────────────────────────────────────

    def _on_press(self, key):
        name = getattr(key, "name", None) or ""
        if any(name in g for g in (_CMD_KEYS, _CTRL_KEYS, _SHIFT_KEYS, _ALT_KEYS)):
            with self._lock:
                self._modifiers.add(name)
            return

        with self._lock:
            mods = set(self._modifiers)

        # 主修飾キーがなければ通常入力 → スキップ
        if not (mods & _PRIMARY_MOD):
            return

        shortcut = self._build_label(key, mods)
        if not shortcut:
            return

        self._record(shortcut)

    def _on_release(self, key):
        name = getattr(key, "name", None) or ""
        with self._lock:
            self._modifiers.discard(name)

    # ── 内部処理 ──────────────────────────────────────────────────────────

    def _build_label(self, key, mods: set[str]) -> str:
        """修飾キー + キー名 の文字列を組み立てる。"""
        parts = [_PRIMARY_LABEL]
        if mods & _SHIFT_KEYS:
            parts.append("Shift")
        if mods & _ALT_KEYS:
            parts.append(_ALT_LABEL)
        key_str = _key_name(key)
        if not key_str:
            return ""
        parts.append(key_str)
        return "+".join(parts)

    def _record(self, shortcut: str):
        app_name, _ = get_active_app_info()
        now = time.monotonic()
        key_id = (app_name, shortcut)

        with self._lock:
            if now - self._last_recorded.get(key_id, 0) < _THROTTLE:
                return
            self._last_recorded[key_id] = now

        self._db.insert_event(
            timestamp=datetime.now().isoformat(),
            event_type="shortcut",
            app_name=app_name,
            window_title=shortcut,
        )
