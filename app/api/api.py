from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from app.services.parser import parse_resume
from app.services.github_analyzer import analyze_github_profile
from app.services.ai import analyze_portfolio
from app.services.tts import generate_speech

router = APIRouter()


@router.post("/analyze")
async def analyze_candidate(
    resume: UploadFile = File(None, description="PDF или DOCX файл резюме"),
    resume_text: str = Form(None, description="Текст резюме (альтернатива файлу)"),
    github_username: Optional[str] = Form(None, description="GitHub username (опционально)"),
    generate_audio: bool = Form(True, description="Генерировать аудио")
):
    """Анализирует резюме и GitHub профиль"""
    
    # Валидация: должно быть ИЛИ файл, ИЛИ текст
    if not resume and not resume_text:
        raise HTTPException(400, "Загрузи файл или вставь текст резюме")
    
    # Получаем текст резюме
    try:
        if resume and resume.filename:
            # Режим файла
            if not resume.filename.lower().endswith(('.pdf', '.docx', '.doc')):
                raise HTTPException(400, "Поддерживаются только PDF и DOCX файлы")
            
            file_bytes = await resume.read()
            
            if len(file_bytes) == 0:
                raise HTTPException(400, "Файл пустой")
            
            text = parse_resume(file_bytes, resume.filename)
            
            if not text or len(text.strip()) < 50:
                raise HTTPException(400, "Не удалось извлечь текст из файла. Попробуй вставить текст вручную.")
        else:
            # Режим текста
            text = resume_text.strip()
            if len(text) < 100:
                raise HTTPException(400, f"Минимум 100 символов. Сейчас: {len(text)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки резюме: {str(e)}")
    
    print(f"📄 Получен текст резюме: {len(text)} символов")
    
    # GitHub анализируем ТОЛЬКО если указан
    github_data = None
    if github_username and github_username.strip():
        try:
            github_data = await analyze_github_profile(github_username.strip())
        except Exception as e:
            print(f"⚠️ Ошибка GitHub: {e}")
            github_data = {"error": f"Не удалось получить GitHub: {str(e)}"}
    
    # AI анализ
    try:
        analysis = await analyze_portfolio(text, github_data)
    except Exception as e:
        print(f"❌ Ошибка AI: {e}")
        raise HTTPException(500, f"Ошибка AI анализа: {str(e)}")
    
    # Озвучка
    audio_base64 = None
    if generate_audio and analysis.get("tts_summary"):
        try:
            audio_base64 = await generate_speech(
                text=analysis["tts_summary"],
                voice="male"
            )
        except Exception as e:
            print(f"⚠️ Ошибка TTS: {e}")
    
    return JSONResponse({
        "analysis": analysis,
        "github_profile": github_data,
        "audio": audio_base64
    })


@router.get("/health")
async def health():
    """Проверка работоспособности API"""
    return {
        "status": "OK",
        "service": "РезюмеAI",
        "version": "2.0.0"
    }