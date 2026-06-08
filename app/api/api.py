from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from app.services.parser import parse_resume
from app.services.github_analyzer import analyze_github_profile
from app.services.ai import analyze_portfolio, generate_cover_letter, analyze_match_score
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
    
    if not resume and not resume_text:
        raise HTTPException(400, "Загрузи файл или вставь текст резюме")
    
    try:
        if resume and resume.filename:
            if not resume.filename.lower().endswith(('.pdf', '.docx')):
                raise HTTPException(400, "Поддерживаются только PDF и DOCX файлы")
            
            file_bytes = await resume.read()
            if len(file_bytes) == 0:
                raise HTTPException(400, "Файл пустой")
            
            text = parse_resume(file_bytes, resume.filename)
            if not text or len(text.strip()) < 50:
                raise HTTPException(400, "Не удалось извлечь текст. Попробуй вставить вручную.")
        else:
            text = resume_text.strip()
            if len(text) < 100:
                raise HTTPException(400, f"Минимум 100 символов. Сейчас: {len(text)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки резюме: {str(e)}")
    
    print(f"📄 Получен текст резюме: {len(text)} символов")
    
    github_data = None
    if github_username and github_username.strip():
        try:
            github_data = await analyze_github_profile(github_username.strip())
        except Exception as e:
            print(f"⚠️ Ошибка GitHub: {e}")
            github_data = {"error": f"Не удалось получить GitHub: {str(e)}"}
    
    try:
        analysis = await analyze_portfolio(text, github_data)
    except Exception as e:
        print(f"❌ Ошибка AI: {e}")
        raise HTTPException(500, f"Ошибка AI анализа: {str(e)}")
    
    audio_base64 = None
    if generate_audio and analysis.get("tts_summary"):
        try:
            audio_base64 = await generate_speech(text=analysis["tts_summary"], voice="male")
        except Exception as e:
            print(f"⚠️ Ошибка TTS: {e}")
    
    return JSONResponse({
        "analysis": analysis,
        "github_profile": github_data,
        "audio": audio_base64
    })


@router.post("/generate-cover-letter")
async def generate_cover_letter_endpoint(
    resume: UploadFile = File(None, description="PDF или DOCX файл резюме"),
    resume_text: str = Form(None, description="Текст резюме"),
    company_name: str = Form(..., description="Название компании"),
    job_description: str = Form(..., description="Описание вакансии"),
    generate_audio: bool = Form(True, description="Озвучить письмо голосом")
):
    """Генерирует Cover Letter и озвучивает его"""
    
    try:
        if resume and resume.filename:
            if not resume.filename.lower().endswith(('.pdf', '.docx')):
                raise HTTPException(400, "Только PDF и DOCX")
            file_bytes = await resume.read()
            text = parse_resume(file_bytes, resume.filename)
        elif resume_text:
            text = resume_text.strip()
        else:
            raise HTTPException(400, "Нужно резюме (файл или текст)")
            
        if len(text) < 50:
            raise HTTPException(400, "Слишком мало текста в резюме")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка резюме: {str(e)}")

    if not company_name.strip():
        raise HTTPException(400, "Укажи название компании")
    
    if not job_description.strip() or len(job_description) < 50:
        raise HTTPException(400, "Описание вакансии слишком короткое (минимум 50 символов)")

    try:
        letter = await generate_cover_letter(
            resume_text=text,
            company_name=company_name.strip(),
            job_description=job_description.strip()
        )
        
        if not letter or len(letter) < 100:
            raise HTTPException(500, "AI вернул слишком короткий ответ")
    except HTTPException:
        raise
    except Exception as e:
        print(f" Ошибка генерации Cover Letter: {e}")
        raise HTTPException(500, f"Ошибка генерации: {str(e)}")

    audio_base64 = None
    if generate_audio:
        try:
            print(f"🔊 Озвучиваю Cover Letter ({len(letter)} символов)...")
            audio_base64 = await generate_speech(text=letter, voice="male")
            print("✅ Аудио сгенерировано")
        except Exception as e:
            print(f"⚠️ Ошибка TTS для Cover Letter: {e}")
    
    return {
        "cover_letter": letter,
        "audio": audio_base64
    }


@router.post("/match-score")
async def match_score_endpoint(
    resume: UploadFile = File(None, description="PDF или DOCX файл резюме"),
    resume_text: str = Form(None, description="Текст резюме"),
    job_description: str = Form(..., description="Описание вакансии"),
    generate_audio: bool = Form(True, description="Озвучить результат")
):
    """Анализирует соответствие резюме вакансии и озвучивает вердикт"""
    
    # 1. Получаем текст резюме
    try:
        if resume and resume.filename:
            if not resume.filename.lower().endswith(('.pdf', '.docx')):
                raise HTTPException(400, "Только PDF и DOCX")
            file_bytes = await resume.read()
            text = parse_resume(file_bytes, resume.filename)
        elif resume_text:
            text = resume_text.strip()
        else:
            raise HTTPException(400, "Нужно резюме (файл или текст)")
            
        if len(text) < 50:
            raise HTTPException(400, "Слишком мало текста в резюме")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка резюме: {str(e)}")

    # 2. Валидация вакансии
    if not job_description.strip() or len(job_description) < 50:
        raise HTTPException(400, "Описание вакансии слишком короткое (минимум 50 символов)")

    # 3. Анализ Match Score
    try:
        print(f"🎯 Анализирую соответствие вакансии...")
        match_data = await analyze_match_score(
            resume_text=text,
            job_description=job_description.strip()
        )
    except Exception as e:
        print(f"❌ Ошибка Match Score AI: {e}")
        raise HTTPException(500, f"Ошибка анализа: {str(e)}")

    # 4. Озвучка вердикта
    audio_base64 = None
    if generate_audio and match_data.get("tts_summary"):
        try:
            print(f"🔊 Озвучиваю вердикт...")
            audio_base64 = await generate_speech(text=match_data["tts_summary"], voice="male")
        except Exception as e:
            print(f"⚠️ Ошибка TTS для Match Score: {e}")

    return {
        "match_score": match_data,
        "audio": audio_base64
    }


@router.get("/health")
async def health():
    """Проверка работоспособности API"""
    return {
        "status": "OK",
        "service": "РезюмеAI",
        "version": "2.0.0"
    }