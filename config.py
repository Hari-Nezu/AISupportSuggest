import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ACTIVITY_LOG_FILE = DATA_DIR / "activity_log.jsonl"

# Anthropic API（デフォルト）
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USE_ANTHROPIC = True

# Ollama（ローカルLLMへの切り替えオプション）
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
OLLAMA_VISION_MODEL = "llava"  # スクリーンショットモード時に使用

# Activity logger
LOG_INTERVAL_MINUTES = 5

# スクリーンショットモード
# True にすると5分ごとにスクリーンショットも記録し、分析時に画像を送信する
# macOS の「画面収録」権限が必要
SCREENSHOT_MODE = False
SCREENSHOT_DIR = DATA_DIR / "screenshots"
SCREENSHOT_MAX_SEND = 12  # 分析時に送る最大枚数（均等サンプリング）

# 収録のみモード
# True にすると LLM API を一切呼ばず、ログ・スクリーンショットの記録だけ行う
RECORD_ONLY = False

# Scheduler: 何時に分析するか（0 = 深夜0時）
ANALYSIS_HOUR = 0
ANALYSIS_MINUTE = 0
