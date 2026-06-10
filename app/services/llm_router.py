"""
Универсальный роутер для работы с разными LLM провайдерами.
Переключайся между Ollama и YandexGPT одной переменной в .env
"""

import httpx
import time
import logging
import json
from openai import OpenAI
from app.config import (
    LLM_PROVIDER, OLLAMA_URL, OLLAMA_MODEL,
    YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_MODEL,
    REQUEST_TIMEOUT, get_active_provider
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем клиент OpenAI для Yandex Cloud
yandex_client = OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
)


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> str:
    """
    Универсальная функция вызова LLM.
    Автоматически выбирает провайдера из .env
    """
    start_time = time.time()
    provider_info = get_active_provider()
    
    logger.info(f"🤖 Вызов LLM: {provider_info['provider']} | Модель: {provider_info['model']}")
    logger.debug(f"Температура: {temperature}, Max tokens: {max_tokens}")
    logger.debug(f"System prompt: {system_prompt[:100]}...")
    logger.debug(f"User prompt: {user_prompt[:200]}...")
    
    try:
        if LLM_PROVIDER == "ollama":
            result = await call_ollama(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif LLM_PROVIDER == "yandexgpt":
            result = await call_yandexgpt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            raise ValueError(f"Неизвестный провайдер: {LLM_PROVIDER}")
        
        elapsed = time.time() - start_time
        logger.info(f"✅ LLM ответ получен за {elapsed:.2f}с | Длина: {len(result)} символов")
        logger.debug(f"Ответ: {result[:200]}...")
        
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Ошибка LLM через {elapsed:.2f}с: {type(e).__name__}: {str(e)}")
        raise


async def call_ollama(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 8046
) -> str:
    """Вызов локальной модели Ollama"""
    chat_url = str(OLLAMA_URL).replace("/api/generate", "/api/chat")
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": 4096,
            "top_p": 0.9,
            "top_k": 40
        }
    }
    
    logger.info(f"📤 Отправка запроса к Ollama: {chat_url}")
    logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False)[:300]}...")
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(chat_url, json=payload)
            response.raise_for_status()
            result = response.json()
        
        logger.info(f"✅ Ollama ответ получен")
        logger.debug(f"Ollama raw response: {result}")
        
        content = result.get("message", {}).get("content", "").strip()
        logger.debug(f"Извлечен контент: {len(content)} символов")
        
        return content
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP ошибка Ollama: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"❌ Ошибка запроса к Ollama: {e}")
        logger.error(f"Проверьте, что Ollama запущен на {OLLAMA_URL}")
        raise
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка Ollama: {type(e).__name__}: {str(e)}")
        raise

async def call_yandexgpt(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 16000
) -> str:
    """Вызов модели через Yandex Cloud OpenAI-совместимый API"""
    
    model_uri = f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}"
    
    logger.info(f"📤 Отправка запроса к YandexGPT: {model_uri}")
    logger.debug(f"Folder ID: {YANDEX_FOLDER_ID}")
    
    try:
        logger.debug(f"Отправка messages: system={len(system_prompt)}, user={len(user_prompt)} символов")
        
        response = yandex_client.chat.completions.create(
            model=model_uri,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        logger.info(f"✅ YandexGPT ответ получен")
        logger.debug(f"Raw response: {response}")
        
        if not response.choices:
            logger.error("❌ YandexGPT вернул пустой список choices")
            raise ValueError(f"Модель вернула пустой ответ")
        
        choice = response.choices[0]
        message = choice.message
        
        # Проверяем все возможные поля с ответом
        content = None
        
        # Приоритет 1: обычное content
        if hasattr(message, 'content') and message.content:
            content = message.content.strip()
            logger.info("📝 Использован content")
        
        # Приоритет 2: reasoning_content (для thinking-моделей)
        elif hasattr(message, 'reasoning_content') and message.reasoning_content:
            content = message.reasoning_content.strip()
            logger.info("🧠 Использован reasoning_content (thinking mode)")
            logger.warning("⚠️ Модель работает в режиме рассуждения - ответ может содержать размышления")
        
        # Приоритет 3: пробуем другие варианты
        else:
            logger.error(f"❌ Нет контента в ответе. Message: {message}")
            logger.error(f"Доступные поля: {dir(message)}")
            raise ValueError(f"Модель вернула пустой ответ")
        
        if not content:
            raise ValueError(f"Модель вернула пустой content")
        
        # Логируем статистику
        if hasattr(response, 'usage') and response.usage:
            logger.info(f"📊 Токены: input={response.usage.prompt_tokens}, "
                       f"output={response.usage.completion_tokens}, "
                       f"total={response.usage.total_tokens}")
        
        logger.debug(f"Извлечен контент: {len(content)} символов")
        logger.debug(f"Текст: {content[:300]}...")
        
        return content
        
    except Exception as e:
        logger.error(f"❌ Ошибка YandexGPT: {type(e).__name__}: {str(e)}")
        
        if hasattr(e, 'response'):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        
        raise