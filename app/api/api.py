from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.services.parser import parse_resume_pdf
from app.services.github_analyzer import analyze_github_profile
from app.services.ai import analyze_portfolio
from app.services.tts import generate_speech

router = APIRouter()


@router.post("/analyze")
async def analyze_candidate(
    resume: UploadFile = File(..., description="PDF резюме"),
    github_username: Optional[str] = Form(None, description="GitHub username (опционально)"),
    generate_audio: bool = Form(True, description="Генерировать аудио")
):
    # Проверка файла
    if not resume.filename or not resume.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Загрузите PDF файл")
    
    # Парсинг резюме
    try:
        file_bytes = await resume.read()
        resume_text = parse_resume_pdf(file_bytes)
        
        if not resume_text.strip():
            raise HTTPException(400, "Не удалось извлечь текст из PDF")
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Ошибка парсинга PDF: {str(e)}")
    
    # GitHub анализируем ТОЛЬКО если указан
    github_data = None
    if github_username and github_username.strip():
        try:
            github_data = await analyze_github_profile(github_username.strip())
        except Exception as e:
            github_data = {"error": f"Не удалось получить GitHub: {str(e)}"}
    
    # AI анализ (работает и без GitHub)
    try:
        analysis = await analyze_portfolio(resume_text, github_data)
    except Exception as e:
        raise HTTPException(500, detail=f"Ошибка AI анализа: {str(e)}")
    
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
    
    return {
        "analysis": analysis,
        "github_profile": github_data,
        "audio": audio_base64
    }

@router.get("/health")
async def health():
    """Проверка работоспособности API"""
    return {
        "status": "OK",
        "service": "Portfolio Roaster",
        "version": "2.0.0"
    }