"""
AI-сервис для анализа резюме, генерации Cover Letter и оценки соответствия вакансии.
"""

import json
import re
import logging
from typing import Optional, Dict, Any

from app.config.config import MAX_TEXT_LENGTH
from app.ai.llm_router import LLMRouter
from app.ai.prompts import (
    RESUME_ANALYSIS_PROMPT,
    MATCH_SCORE_PROMPT,
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_TEMPLATE,
)
from app.ai.json_parser import JSONParser

logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    """AI-анализ резюме: разбор, Cover Letter, Match Score."""

    @staticmethod
    async def analyze_portfolio(
        resume_text: str,
        github_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Анализирует резюме + портфолио и возвращает отчёт."""
        context = f"РЕЗЮМЕ КАНДИДАТА:\n{resume_text[:MAX_TEXT_LENGTH]}\n\n"

        if github_data and "error" not in github_data:
            context += (
                f"ПОРТФОЛИО/GITHUB:\n"
                f"- Публичных проектов: {github_data.get('public_repos', 0)}\n"
                f"- Всего звёзд/лайков: {github_data.get('total_stars', 0)}\n"
                f"- Основные технологии: {github_data.get('top_languages', {})}\n"
                f"- Топ проекты: {json.dumps(github_data.get('top_repos', [])[:5], ensure_ascii=False)}\n"
            )
        else:
            context += "Портфолио/GitHub не предоставлено\n"

        raw_text = await LLMRouter.call_llm(
            system_prompt=RESUME_ANALYSIS_PROMPT,
            user_prompt=f"ДАННЫЕ КАНДИДАТА:\n{context}",
            temperature=0.6,
            max_tokens=2048
        )

        logger.info(f"📝 Resume analysis raw length: {len(raw_text)}")
        return JSONParser.parse_safely(raw_text, "Resume analysis")

    @staticmethod
    async def generate_cover_letter(
        resume_text: str,
        company_name: str,
        job_description: str
    ) -> str:
        """Генерирует Cover Letter на основе резюме и вакансии."""
        user_prompt = COVER_LETTER_USER_TEMPLATE.format(
            resume_text=resume_text[:3000],
            company_name=company_name,
            job_description=job_description[:2000]
        )

        letter = await LLMRouter.call_llm(
            system_prompt=COVER_LETTER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1024
        )

        # Очистка от markdown
        letter = re.sub(r"[*#`\[\]]", "", letter).strip()

        if len(letter) < 50:
            raise ValueError("AI вернул слишком короткий Cover Letter")

        return letter

    @staticmethod
    async def analyze_match_score(
        resume_text: str,
        job_description: str
    ) -> Dict[str, Any]:
        """Анализирует соответствие резюме вакансии."""
        user_prompt = f"""{MATCH_SCORE_PROMPT}

                        РЕЗЮМЕ КАНДИДАТА:
                        {resume_text[:3000]}

                        ОПИСАНИЕ ВАКАНСИИ:
                        {job_description[:2000]}"""

        raw_text = await LLMRouter.call_llm(
            system_prompt="Ты — Senior HR. Оценивай честно, конкретно, но поддерживающе.",
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=1024
        )

        logger.info(f"📝 Match score raw length: {len(raw_text)}")
        return JSONParser.parse_safely(raw_text, "Match score")