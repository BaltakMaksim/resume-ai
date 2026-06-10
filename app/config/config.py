import os
from dotenv import load_dotenv

load_dotenv()


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# ============================================
# OLLAMA (локальная модель)
# ============================================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
VOICE = os.getenv("VOICE", "male")

# ============================================
# YANDEXGPT (облачный API)
# ============================================
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt-lite") 

# ============================================
# ОБЩИЕ НАСТРОЙКИ
# ============================================
MAX_TEXT_LENGTH = 2000
REQUEST_TIMEOUT = 600  # 10 минут

# GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Проверка настроек
def get_active_provider():
    if LLM_PROVIDER == "ollama":
        return {
            "provider": "Ollama (локально)",
            "model": OLLAMA_MODEL,
            "url": OLLAMA_URL,
            "cost": "0 ₽"
        }
    elif LLM_PROVIDER == "yandexgpt":
        if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
            raise ValueError("❌ YANDEX_API_KEY и YANDEX_FOLDER_ID не настроены в .env!")
        return {
            "provider": "YandexGPT (облако)",
            "model": YANDEX_MODEL,
            "cost": "~0.45 ₽ за запрос"
        }
    else:
        raise ValueError(f"❌ Неизвестный провайдер: {LLM_PROVIDER}")