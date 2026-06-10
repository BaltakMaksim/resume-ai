import edge_tts
import logging
from app.config import VOICE
import base64

logger = logging.getLogger(__name__)

async def generate_speech(text: str, voice: str = "ru-RU-DmitryNeural") -> bytes:
    """Генерация речи через Edge TTS"""
    
    if not text or not text.strip():
        logger.error("❌ Пустой текст для TTS")
        raise ValueError("Текст для озвучки пустой")
    
    logger.info(f"🎤 Генерация речи: голос={voice}, длина={len(text)} символов")
    logger.debug(f"Текст: {text[:100]}...")
    
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        
        # Собираем аудио в память
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        if not audio_data:
            logger.error("❌ Edge TTS не вернул аудио данные")
            raise ValueError("No audio was received from Edge TTS")
        
        logger.info(f"✅ Аудио сгенерировано: {len(audio_data)} байт")
        return base64.b64encode(audio_data).decode('utf-8')
        
    except Exception as e:
        logger.error(f"❌ Ошибка Edge TTS: {type(e).__name__}: {str(e)}")
        logger.error(f"Параметры: voice={voice}, text_length={len(text)}")
        raise