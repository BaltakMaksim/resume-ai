import edge_tts
import logging
import base64
from typing import Optional, Literal
from pathlib import Path

logger = logging.getLogger(__name__)


class VoiceEngine:
    """
    Движок синтеза речи через Edge TTS.
    
    Использование:
        # С голосом по умолчанию (из .env)
        engine = VoiceEngine()
        audio_b64 = await engine.generate_speech("Привет, мир!")
        
        # С конкретным голосом
        engine = VoiceEngine(voice="female")
        audio_b64 = await engine.generate_speech("Привет, мир!")
        
        # С кастомным голосом Edge TTS
        engine = VoiceEngine(voice="ru-RU-DmitryNeural")
        audio_b64 = await engine.generate_speech("Привет, мир!")
        
        # Сохранение в файл
        await engine.save_to_file("Привет, мир!", "output.mp3")
    """
    
    # Предопределённые голоса
    MALE_VOICE = "ru-RU-DmitryNeural"
    FEMALE_VOICE = "ru-RU-SvetlanaNeural"
    FEMALE_VOICE_ALT = "ru-RU-DariyaNeural"
    
    # Маппинг простых имён на реальные голоса
    VOICE_MAP = {
        "male": MALE_VOICE,
        "female": FEMALE_VOICE,
        "female_alt": FEMALE_VOICE_ALT,
    }
    
    def __init__(self, voice: Optional[str] = None):
        """
        Инициализация движка озвучки.
        
        Args:
            voice: Голос для синтеза. Может быть:
                - "male" / "female" / "female_alt" (из VOICE_MAP)
                - Полный код голоса Edge TTS (например, "ru-RU-DmitryNeural")
                - None (используется голос из .env)
        """
        self.voice = self._resolve_voice(voice)
        logger.info(f"🎙️ VoiceEngine инициализирован с голосом: {self.voice}")
    
    def _resolve_voice(self, voice: Optional[str]) -> str:
        """Преобразует короткое имя голоса в полный код Edge TTS."""
        if voice is None:
            # Импорт здесь, чтобы избежать circular import
            from app.config.config import VOICE
            return VOICE
        
        # Если это короткий алиас из VOICE_MAP
        if voice.lower() in self.VOICE_MAP:
            return self.VOICE_MAP[voice.lower()]
        
        # Если это полный код голоса (содержит дефис)
        if "-" in voice:
            return voice
        
        # По умолчанию — мужской голос
        logger.warning(f"⚠️ Неизвестный голос '{voice}', используем {self.MALE_VOICE}")
        return self.MALE_VOICE
    
    async def generate_speech(self, text: str, voice: Optional[str] = None) -> str:
        """Генерирует речь из текста и возвращает base64-encoded аудио."""
        
        if not text or not text.strip():
            logger.error("❌ Пустой текст для TTS")
            raise ValueError("Текст для озвучки пустой")
        
        actual_voice = self._resolve_voice(voice) if voice else self.voice
        
        logger.info(f"🎤 Генерация речи: голос={actual_voice}, длина={len(text)} символов")
        logger.debug(f"Текст: {text[:100]}...")
        
        try:
            communicate = edge_tts.Communicate(text, actual_voice)
            
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio" and "data" in chunk:
                    audio_data += chunk["data"]
            
            if not audio_data:
                logger.error("❌ Edge TTS не вернул аудио данные")
                raise ValueError("Edge TTS не вернул аудио данные")
            
            logger.info(f"✅ Аудио сгенерировано: {len(audio_data)} байт")
            
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            logger.debug(f"Base64 длина: {len(audio_b64)} символов")
            
            return audio_b64
            
        except ValueError:
            # Перебрасываем ValueError без обёртки
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка Edge TTS: {type(e).__name__}: {str(e)}")
            logger.error(f"Параметры: voice={actual_voice}, text_length={len(text)}")
            raise
    
    async def save_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> Path:
        """
        Генерирует речь и сохраняет в файл.
        
        Args:
            text: Текст для озвучки
            output_path: Путь для сохранения файла
            voice: Опционально переопределить голос
            
        Returns:
            Path к сохранённому файлу
        """
        logger.info(f"💾 Сохранение аудио в файл: {output_path}")
        
        # Генерируем аудио (без base64)
        actual_voice = self._resolve_voice(voice) if voice else self.voice
        communicate = edge_tts.Communicate(text, actual_voice)
        
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and "data" in chunk:
                audio_data += chunk["data"]
        
        if not audio_data:
            raise ValueError("No audio was received from Edge TTS")
        
        # Сохраняем в файл
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(audio_data)
        
        logger.info(f"✅ Аудио сохранено: {output_file} ({len(audio_data)} байт)")
        return output_file
    
    async def get_audio_duration(self, text: str, voice: Optional[str] = None) -> float:
        """
        Вычисляет примерную длительность аудио в секундах.
        
        Args:
            text: Текст для оценки
            voice: Опционально переопределить голос
            
        Returns:
            Примерная длительность в секундах
        """
        # Грубая оценка: ~15 символов в секунду для русского языка
        estimated_duration = len(text) / 15.0
        logger.debug(f"⏱️ Примерная длительность: {estimated_duration:.1f}с")
        return estimated_duration
    
    @classmethod
    async def list_voices(cls, language: str = "ru") -> list[dict]:
        """
        Возвращает список доступных голосов Edge TTS.
        
        Args:
            language: Фильтр по языку (например, "ru", "en")
            
        Returns:
            Список словарей с информацией о голосах
        """
        logger.info(f"🔍 Получение списка голосов для языка: {language}")
        
        voices = await edge_tts.list_voices()
        
        # Фильтруем по языку
        filtered_voices = [
            {
                "name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"],
                "friendly_name": v.get("FriendlyName", v["ShortName"]),
            }
            for v in voices
            if v["Locale"].startswith(language)
        ]
        
        logger.info(f"✅ Найдено {len(filtered_voices)} голосов")
        return filtered_voices
    
    @classmethod
    async def quick_speak(cls, text: str, voice: str = "male") -> str:
        """
        Быстрая генерация речи без создания экземпляра класса.
        
        Args:
            text: Текст для озвучки
            voice: Голос ("male", "female" или полный код)
            
        Returns:
            Base64-encoded аудио
        """
        engine = cls(voice=voice)
        return await engine.generate_speech(text)