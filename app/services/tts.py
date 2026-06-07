import edge_tts
import asyncio
import base64
from pathlib import Path
import uuid

# Папка для временных аудиофайлов
AUDIO_DIR = Path("app/audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Голоса для русского языка
RU_VOICES = {
    "male": "ru-RU-DmitryNeural",      # Мужской
    "female": "ru-RU-SvetlanaNeural",  # Женский
}

async def generate_speech(text: str, voice: str = "male") -> str:
    """
    Генерирует аудио из текста и возвращает base64 строку
    
    Args:
        text: Текст для озвучки
        voice: "male" или "female"
    
    Returns:
        Base64 encoded audio (MP3)
    """
    # Выбираем голос
    voice_name = RU_VOICES.get(voice, RU_VOICES["male"])
    
    # Генерируем уникальное имя файла
    filename = f"{uuid.uuid4()}.mp3"
    filepath = AUDIO_DIR / filename
    
    try:
        # Создаем аудио через Edge TTS
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(str(filepath))
        
        # Читаем файл и конвертируем в base64
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        return audio_base64
        
    except Exception as e:
        print(f"Ошибка генерации речи: {e}")
        return ""
        
    finally:
        # Очищаем старые файлы (опционально)
        await _cleanup_old_files()

async def _cleanup_old_files(max_files: int = 10):
    """Удаляет старые аудиофайлы, оставляя только последние"""
    try:
        files = sorted(AUDIO_DIR.glob("*.mp3"), key=lambda x: x.stat().st_mtime)
        while len(files) > max_files:
            files[0].unlink()
            files.pop(0)
    except Exception as e:
        print(f"Ошибка очистки аудио: {e}")