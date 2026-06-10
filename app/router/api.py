"""
Роутер API для РезюмеAI.
Эндпоинты: анализ резюме, Cover Letter, Match Score, health check.
"""

import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.parser_document import DocumentParser
from app.services.github_analyzer import GitHubAnalyzer
from app.services.voice_engine import VoiceEngine
from app.ai.ai_service import ResumeAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton-сервисы (создаются один раз)
document_parser = DocumentParser(max_size_mb=10)
github_analyzer = GitHubAnalyzer()
voice_engine = VoiceEngine()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def _extract_resume_text(
    resume: Optional[UploadFile],
    resume_text: Optional[str],
    min_length: int = 100
) -> str:
    """
    Извлекает текст резюме из файла или строки.
    Общая логика для всех эндпоинтов.
    """
    if resume and resume.filename:
        ext = resume.filename.lower()
        if not ext.endswith(('.pdf', '.docx')):
            raise HTTPException(400, "Поддерживаются только PDF и DOCX файлы")
        
        file_bytes = await resume.read()
        if not file_bytes:
            raise HTTPException(400, "Файл пустой")
        
        try:
            text = document_parser.parse(file_bytes, resume.filename)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга файла: {e}")
            raise HTTPException(500, f"Ошибка обработки файла: {str(e)}")
    elif resume_text:
        text = resume_text.strip()
    else:
        raise HTTPException(400, "Загрузи файл или вставь текст резюме")
    
    if len(text) < min_length:
        raise HTTPException(
            400,
            f"Слишком мало текста в резюме. Минимум {min_length} символов, сейчас: {len(text)}"
        )
    
    logger.info(f"📄 Получен текст резюме: {len(text)} символов")
    return text


async def _generate_audio_safe(text: str, voice: str = "male") -> Optional[str]:
    """Безопасно генерирует аудио, возвращает None при ошибке."""
    try:
        return await voice_engine.generate_speech(text, voice=voice)
    except Exception as e:
        logger.warning(f"⚠️ Ошибка TTS (не критично): {e}")
        return None


# ============================================
# ЭНДПОИНТЫ
# ============================================

@router.post("/analyze")
async def analyze_candidate(
    resume: Optional[UploadFile] = File(None, description="PDF или DOCX файл резюме"),
    resume_text: Optional[str] = Form(None, description="Текст резюме (альтернатива файлу)"),
    github_username: Optional[str] = Form(None, description="GitHub username (опционально)"),
    generate_audio: bool = Form(True, description="Генерировать аудио"),
):
    """Анализирует резюме и GitHub профиль."""
    # 1. Извлекаем текст резюме
    text = await _extract_resume_text(resume, resume_text, min_length=100)
    
    # 2. Анализируем GitHub (если указан)
    github_data = None
    if github_username and github_username.strip():
        try:
            github_data = await github_analyzer.analyze_profile(github_username.strip())
            logger.info(f"✅ GitHub профиль получен: {github_username}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка GitHub: {e}")
            github_data = {"error": f"Не удалось получить GitHub: {str(e)}"}
    
    # 3. AI-анализ резюме
    try:
        analysis = await ResumeAnalyzer.analyze_portfolio(text, github_data)
    except ValueError as e:
        raise HTTPException(500, f"Ошибка AI анализа: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка AI: {e}")
        raise HTTPException(500, f"Ошибка AI анализа: {str(e)}")
    
    # 4. Озвучка
    audio_base64 = None
    if generate_audio and analysis.get("tts_summary"):
        audio_base64 = await _generate_audio_safe(analysis["tts_summary"])
    
    return {
        "analysis": analysis,
        "github_profile": github_data,
        "audio": audio_base64,
    }


@router.post("/generate-cover-letter")
async def generate_cover_letter_endpoint(
    resume: Optional[UploadFile] = File(None, description="PDF или DOCX файл резюме"),
    resume_text: Optional[str] = Form(None, description="Текст резюме"),
    company_name: str = Form(..., description="Название компании"),
    job_description: str = Form(..., description="Описание вакансии"),
    generate_audio: bool = Form(True, description="Озвучить письмо голосом"),
):
    """Генерирует Cover Letter и озвучивает его."""
    # 1. Валидация входных данных
    text = await _extract_resume_text(resume, resume_text, min_length=50)
    
    if not company_name.strip():
        raise HTTPException(400, "Укажи название компании")
    if len(job_description.strip()) < 50:
        raise HTTPException(400, "Описание вакансии слишком короткое (минимум 50 символов)")
    
    # 2. Генерация Cover Letter
    try:
        letter = await ResumeAnalyzer.generate_cover_letter(
            resume_text=text,
            company_name=company_name.strip(),
            job_description=job_description.strip(),
        )
    except ValueError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        logger.error(f"❌ Ошибка генерации Cover Letter: {e}")
        raise HTTPException(500, f"Ошибка генерации: {str(e)}")
    
    # 3. Озвучка
    audio_base64 = None
    if generate_audio:
        audio_base64 = await _generate_audio_safe(letter)
    
    return {
        "cover_letter": letter,
        "audio": audio_base64,
    }


@router.post("/match-score")
async def match_score_endpoint(
    resume: Optional[UploadFile] = File(None, description="PDF или DOCX файл резюме"),
    resume_text: Optional[str] = Form(None, description="Текст резюме"),
    job_description: str = Form(..., description="Описание вакансии"),
    generate_audio: bool = Form(True, description="Озвучить результат"),
):
    """Анализирует соответствие резюме вакансии и озвучивает вердикт."""
    # 1. Получаем текст резюме
    text = await _extract_resume_text(resume, resume_text, min_length=50)
    
    # 2. Валидация вакансии
    if len(job_description.strip()) < 50:
        raise HTTPException(400, "Описание вакансии слишком короткое (минимум 50 символов)")
    
    # 3. Анализ Match Score
    try:
        match_data = await ResumeAnalyzer.analyze_match_score(
            resume_text=text,
            job_description=job_description.strip(),
        )
    except ValueError as e:
        raise HTTPException(500, f"Ошибка анализа: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Ошибка Match Score: {e}")
        raise HTTPException(500, f"Ошибка анализа: {str(e)}")
    
    # 4. Озвучка вердикта
    audio_base64 = None
    if generate_audio and match_data.get("tts_summary"):
        audio_base64 = await _generate_audio_safe(match_data["tts_summary"])
    
    return {
        "match_score": match_data,
        "audio": audio_base64,
    }


@router.get("/health")
async def health():
    """Проверка работоспособности API."""
    return {
        "status": "OK",
        "service": "РезюмеAI",
        "version": "2.0.0",
    }