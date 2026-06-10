"""
Универсальный роутер для работы с разными LLM провайдерами.
Переключайся между Ollama и YandexGPT одной переменной в .env
"""

import httpx
import time
import logging
import json
from typing import Optional
from openai import OpenAI
from app.config.config import (
    LLM_PROVIDER, OLLAMA_URL, OLLAMA_MODEL,
    YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_MODEL,
    REQUEST_TIMEOUT, get_active_provider
)

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Универсальный роутер LLM-провайдеров.
    
    Все методы статические — класс работает как namespace,
    не требует инстанцирования. Клиент YandexGPT создаётся лениво
    при первом обращении.
    
    Использование:
        result = await LLMRouter.call_llm(
            system_prompt="Ты HR-ассистент",
            user_prompt="Проанализируй резюме..."
        )
    """

    # Ленивая инициализация клиента YandexGPT
    _yandex_client: Optional[OpenAI] = None

    @classmethod
    def _get_yandex_client(cls) -> OpenAI:
        """Возвращает singleton-клиент YandexGPT (создаётся при первом вызове)."""
        if cls._yandex_client is None:
            cls._yandex_client = OpenAI(
                api_key=YANDEX_API_KEY,
                base_url="https://ai.api.cloud.yandex.net/v1",
            )
            logger.info("🔧 Клиент YandexGPT инициализирован")
        return cls._yandex_client

    # =========================================================================
    # ПУБЛИЧНЫЙ ИНТЕРФЕЙС
    # =========================================================================

    @staticmethod
    async def call_llm(
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Универсальный вызов LLM.
        Автоматически выбирает провайдера из .env (LLM_PROVIDER).
        """
        start_time = time.time()
        provider_info = get_active_provider()

        logger.info(f"🤖 Вызов LLM: {provider_info['provider']} | Модель: {provider_info['model']}")
        logger.debug(f"Температура: {temperature}, Max tokens: {max_tokens}")
        logger.debug(f"System prompt: {system_prompt[:100]}...")
        logger.debug(f"User prompt: {user_prompt[:200]}...")

        try:
            if LLM_PROVIDER == "ollama":
                result = await LLMRouter._call_ollama(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            elif LLM_PROVIDER == "yandexgpt":
                result = await LLMRouter._call_yandexgpt(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
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

    # =========================================================================
    # ВНУТРЕННИЕ МЕТОДЫ (приватные)
    # =========================================================================

    @staticmethod
    async def _call_ollama(
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8046,
    ) -> str:
        """Вызов локальной модели Ollama через /api/chat."""
        chat_url = str(OLLAMA_URL).replace("/api/generate", "/api/chat")

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": 4096,
                "top_p": 0.9,
                "top_k": 40,
            },
        }

        logger.info(f"📤 Отправка запроса к Ollama: {chat_url}")
        logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False)[:300]}...")

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(chat_url, json=payload)
                response.raise_for_status()
                result = response.json()

            logger.info("✅ Ollama ответ получен")
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

    @staticmethod
    async def _call_yandexgpt(
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 16000,
    ) -> str:
        """Вызов YandexGPT через OpenAI-совместимый API."""
        client = LLMRouter._get_yandex_client()
        model_uri = f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}"

        logger.info(f"📤 Отправка запроса к YandexGPT: {model_uri}")
        logger.debug(f"Folder ID: {YANDEX_FOLDER_ID}")

        try:
            logger.debug(
                f"Отправка messages: system={len(system_prompt)}, user={len(user_prompt)} символов"
            )

            response = client.chat.completions.create(
                model=model_uri,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            logger.info("✅ YandexGPT ответ получен")
            logger.debug(f"Raw response: {response}")

            if not response.choices:
                logger.error("❌ YandexGPT вернул пустой список choices")
                raise ValueError("Модель вернула пустой ответ")

            choice = response.choices[0]
            message = choice.message

            # === Безопасное извлечение контента ===
            # Приоритет 1: обычный content
            content = getattr(message, "content", None)
            source = "content"

            # Приоритет 2: reasoning_content (thinking-режим)
            if not content:
                content = getattr(message, "reasoning_content", None)
                source = "reasoning_content"
                if content:
                    logger.warning(
                        "⚠️ Модель работает в режиме рассуждения - ответ может содержать размышления"
                    )

            if not content:
                logger.error(f"❌ Нет контента в ответе. Message: {message}")
                logger.error(f"Доступные поля: {dir(message)}")
                raise ValueError("Модель вернула пустой ответ")

            content = content.strip()
            logger.info(f"📝 Использован источник: {source}")

            # Логируем статистику по токенам
            usage = getattr(response, "usage", None)
            if usage:
                logger.info(
                    f"📊 Токены: input={usage.prompt_tokens}, "
                    f"output={usage.completion_tokens}, "
                    f"total={usage.total_tokens}"
                )

            logger.debug(f"Извлечен контент: {len(content)} символов")
            logger.debug(f"Текст: {content[:300]}...")

            return content

        except Exception as e:
            logger.error(f"❌ Ошибка YandexGPT: {type(e).__name__}: {str(e)}")

            response_obj = getattr(e, "response", None)
            if response_obj is not None:
                logger.error(f"Response status: {response_obj.status_code}")
                logger.error(f"Response body: {response_obj.text}")

            raise