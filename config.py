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

# Activity logger
LOG_INTERVAL_MINUTES = 5

# Scheduler: 何時に分析するか（0 = 深夜0時）
ANALYSIS_HOUR = 0
ANALYSIS_MINUTE = 0
