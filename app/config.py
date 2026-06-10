import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ===== Ollama =====
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:8b")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))

# ===== GitHub =====
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ===== Edge TTS =====
TTS_VOICE = os.getenv("TTS_VOICE", "ru-RU-DmitryNeural")

# ===== База данных (на будущее) =====
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ===== ЮKassa (на будущее) =====
YUKASSA_SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY", "")
YUKASSA_SHOP_ID = os.getenv("YUKASSA_SHOP_ID", "")

# ===== Режим =====
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "10000"))