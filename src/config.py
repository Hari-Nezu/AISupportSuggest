"""アプリケーション設定。"""
import os
from pathlib import Path

# ── パス ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "activity.db"

# ── LLM バックエンド ─────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USE_ANTHROPIC = True  # False にすると Ollama を使用

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
OLLAMA_VISION_MODEL = "llava"

# ── イベント検出 ─────────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 1        # アクティブウィンドウのポーリング間隔
IDLE_THRESHOLD_SECONDS = 300     # 5分間変化なし → idle 判定

# ── 動作モード ───────────────────────────────────────────────────────────────
RECORD_ONLY = False              # True = LLM API を呼ばず記録のみ

# ── 分析スケジュール ─────────────────────────────────────────────────────────
ANALYSIS_HOUR = 0
ANALYSIS_MINUTE = 0
