"""SQLite データベース操作。"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from src.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    event_type      TEXT    NOT NULL DEFAULT 'app_switch',
    app_name        TEXT    NOT NULL DEFAULT 'Unknown',
    window_title    TEXT    DEFAULT '',
    screenshot_path TEXT,
    duration_seconds REAL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS daily_analysis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,
    phase           TEXT    NOT NULL DEFAULT 'semantic',
    event_count     INTEGER DEFAULT 0,
    app_summary     TEXT,
    analysis_text   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(date, phase)
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
"""


class Database:
    """スレッドセーフな SQLite ラッパー。"""

    def __init__(self, db_path: str | None = None):
        self._db_path = str(db_path or DB_PATH)
        self._local = threading.local()
        self._init_schema()

    # ── 接続管理 ──────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_schema(self):
        conn = sqlite3.connect(self._db_path)
        conn.executescript(_SCHEMA)
        conn.close()

    # ── イベント操作 ──────────────────────────────────────────────────────

    def insert_event(
        self,
        timestamp: str,
        event_type: str,
        app_name: str,
        window_title: str = "",
        screenshot_path: str | None = None,
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO events (timestamp, event_type, app_name, window_title, screenshot_path)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, event_type, app_name, window_title, screenshot_path),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def update_event_duration(self, event_id: int, duration_seconds: float):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE events SET duration_seconds = ? WHERE id = ?",
                (duration_seconds, event_id),
            )

    def get_events_by_date(self, date_str: str) -> list[dict]:
        """指定日のイベントを取得する。date_str は 'YYYY-MM-DD' 形式。"""
        with self._cursor() as cur:
            cur.execute(
                """SELECT * FROM events
                   WHERE date(timestamp) = ?
                   ORDER BY timestamp""",
                (date_str,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_today_events(self) -> list[dict]:
        return self.get_events_by_date(datetime.now().date().isoformat())

    def get_today_event_count(self) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM events WHERE date(timestamp) = date('now','localtime')"
            )
            return cur.fetchone()[0]

    def get_screenshots_by_date(self, date_str: str, max_count: int = 12) -> list[str]:
        """指定日のスクリーンショットパスを均等サンプリングして返す。"""
        with self._cursor() as cur:
            cur.execute(
                """SELECT screenshot_path FROM events
                   WHERE date(timestamp) = ? AND screenshot_path IS NOT NULL
                   ORDER BY timestamp""",
                (date_str,),
            )
            paths = [row[0] for row in cur.fetchall()]
        if not paths or max_count <= 0:
            return []
        if len(paths) <= max_count:
            return paths
        step = len(paths) / max_count
        return [paths[int(i * step)] for i in range(max_count)]

    # ── 分析結果操作 ──────────────────────────────────────────────────────

    def save_analysis(
        self,
        date_str: str,
        phase: str,
        analysis_text: str,
        event_count: int = 0,
        app_summary: str = "",
    ):
        """分析結果を保存（UPSERT）。phase = 'semantic' | 'optimization'"""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO daily_analysis (date, phase, event_count, app_summary, analysis_text)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(date, phase) DO UPDATE SET
                       event_count = excluded.event_count,
                       app_summary = excluded.app_summary,
                       analysis_text = excluded.analysis_text,
                       created_at = datetime('now','localtime')""",
                (date_str, phase, event_count, app_summary, analysis_text),
            )

    def get_analysis(self, date_str: str, phase: str) -> str | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT analysis_text FROM daily_analysis WHERE date = ? AND phase = ?",
                (date_str, phase),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_recent_analyses(self, phase: str, days: int = 7) -> list[dict]:
        """直近N日分の分析結果を取得する。"""
        with self._cursor() as cur:
            cur.execute(
                """SELECT date, analysis_text FROM daily_analysis
                   WHERE phase = ?
                   ORDER BY date DESC LIMIT ?""",
                (phase, days),
            )
            return [dict(row) for row in cur.fetchall()]

    # ── 統計 ──────────────────────────────────────────────────────────────

    def get_app_summary(self, date_str: str) -> dict[str, float]:
        """指定日のアプリ別合計使用秒数を返す。"""
        with self._cursor() as cur:
            cur.execute(
                """SELECT app_name, SUM(COALESCE(duration_seconds, 0)) as total
                   FROM events
                   WHERE date(timestamp) = ?
                   GROUP BY app_name
                   ORDER BY total DESC""",
                (date_str,),
            )
            return {row["app_name"]: row["total"] for row in cur.fetchall()}
