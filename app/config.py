# Конфигурация
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"

# Уменьшаем входной текст чтобы оставить место для ответа
MAX_TEXT_LENGTH = 3000  # Было 4000-6000

# Увеличиваем таймаут (модель может думать долго)
REQUEST_TIMEOUT = 600  # 10 минут

# GitHub
GITHUB_TOKEN = ""