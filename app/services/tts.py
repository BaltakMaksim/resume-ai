import edge_tts
import asyncio
import base64
from pathlib import Path
import uuid
import os

# Папка для временных аудиофайлов
AUDIO_DIR = Path("app/audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Голоса для русского языка (нейросетевые голоса)
RU_VOICES = {
    "male": "ru-RU-DmitryNeural",      # Мужской (Дмитрий)
    "female": "ru-RU-SvetlanaNeural",  # Женский (Светлана)
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
    
    # Генерируем уникальное имя файла, чтобы не было конфликтов
    filename = f"{uuid.uuid4()}.mp3"
    filepath = AUDIO_DIR / filename
    
    print(f"🔊 Начинаю генерацию аудио для файла {filename}...")
    
    try:
        # Создаем аудио через Edge TTS
        # text: текст, voice_name: голос
        communicate = edge_tts.Communicate(text, voice_name)
        
        # Сохраняем файл на диск
        await communicate.save(str(filepath))
        
        # Читаем файл и конвертируем в base64 для отправки на фронтенд
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        print(f"✅ Аудио {filename} успешно сгенерировано ({len(audio_base64)} символов)")
        
        return audio_base64
        
    except Exception as e:
        print(f"❌ Ошибка генерации речи: {e}")
        return ""
        
    finally:
        # Удаляем файл после использования (чтобы не забивать диск)
        # Или используем функцию очистки ниже
        if filepath.exists():
            filepath.unlink() 

async def _cleanup_old_files(max_files: int = 10):
    """Удаляет старые аудиофайлы, оставляя только последние"""
    try:
        if not AUDIO_DIR.exists():
            return
            
        files = list(AUDIO_DIR.glob("*.mp3"))
        # Сортируем по времени изменения
        files.sort(key=lambda x: x.stat().st_mtime)
        
        # Удаляем лишние
        while len(files) > max_files:
            files[0].unlink()
            files.pop(0)
            
    except Exception as e:
        print(f"Ошибка очистки аудио: {e}")