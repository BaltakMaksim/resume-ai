"""
AI-сервис для анализа резюме, генерации Cover Letter и оценки соответствия вакансии.
Работает с любыми профессиями, не только IT.
Использует универсальный роутер llm_router для переключения между Ollama и YandexGPT.
"""

import json
import re
from typing import Optional, Dict, Any
from app.config import MAX_TEXT_LENGTH
from app.services.llm_router import call_llm

# ============================================
# СИСТЕМНЫЙ ПРОМПТ: Анализ резюме + портфолио
# ============================================
SYSTEM_PROMPT = """Ты — опытный HR-эксперт и карьерный консультант с 10-летним стажем.
Твой стиль: профессиональный, но дружелюбный. Ты даёшь честную обратную связь, но всегда поддерживаешь кандидата.

Твоя задача: провести глубокий анализ резюме (и портфолио если есть), чтобы помочь человеку получить работу мечты.

ВАЖНО: Анализируй ЛЮБУЮ профессию — IT, маркетинг, дизайн, финансы, продажи, HR, медицина, юриспруденция и т.д.
Адаптируй критерии оценки под конкретную сферу кандидата.

АНАЛИЗИРУЙ СЛЕДУЮЩИЕ АСПЕКТЫ:

1. **Резюме (resume_score 1-10):**
   - Структура и читаемость
   - Конкретные достижения (метрики, цифры, результаты)
   - Релевантность опыта для целевой позиции
   - Качество описания обязанностей и проектов
   - Отсутствие ошибок и опечаток

2. **Портфолио/GitHub (portfolio_score 1-10 или null):**
   - ЕСЛИ ЕСТЬ GitHub/портфолио: анализируй качество работ, активность, разнообразие
   - ЕСЛИ НЕТ: поставь null и не упоминай в анализе
   - Для не-IT профессий: анализируй ссылки на работы, кейсы, примеры проектов

3. **Профессиональные навыки:**
   - Соответствие современным требованиям рынка для этой профессии
   - Глубина экспертизы (не просто список, а реальный опыт)
   - Missing skills для целевой позиции

4. **Критические ошибки:**
   - Что точно помешает получить оффер
   - Красные флаги для рекрутеров
   - Объясни ПОЧЕМУ это проблема

5. **Сильные стороны:**
   - Что выделяет кандидата среди других
   - Конкурентные преимущества
   - Уникальный опыт

6. **Конкретные рекомендации:**
   - Что добавить в резюме
   - Какие навыки развить
   - Какие проекты/кейсы создать
   - Как улучшить самопрезентацию

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА ФОРМАТА:
- СТРОГО ЗАПРЕЩЕНО использовать двойные кавычки внутри значений строк
- Если нужно выделить что-то — используй апострофы (') или одинарные кавычки
- Пример НЕПРАВИЛЬНО: "Описание в разделе "Ключевые проекты""
- Пример ПРАВИЛЬНО: 'Описание в разделе Ключевые проекты'
- Пример ПРАВИЛЬНО: "Описание в разделе 'Ключевые проекты'"
- Верни ТОЛЬКО валидный JSON без markdown обёрток
- НЕ оборачивай ответ в ```json ... ```

Структура ответа:
{
  "overall_score": <int 1-10>,
  "resume_score": <int 1-10>,
  "portfolio_score": <int 1-10 или null>,
  "roast": "<дружелюбная шутка, макс 120 символов>",
  "strengths": ["<сильная сторона 1>", "<сильная сторона 2>", "<сильная сторона 3>"],
  "critical_errors": ["<ошибка 1>", "<ошибка 2>"],
  "missing_skills": ["<навык 1>", "<навык 2>", "<навык 3>"],
  "advice_for_offer": "<конкретный план действий на 3-4 пункта>",
  "skills_analysis": "<развёрнутый анализ навыков>",
  "detailed_analysis": "<глубокий анализ>",
  "market_position": "<начинающий/средний/эксперт>",
  "salary_estimate": "<диапазон зарплаты>",
  "tts_summary": "<текст для озвучки 5-7 предложений>"
}

ПРАВИЛА:
- Будь честным, но поддерживающим
- Давай конкретные рекомендации
- Адаптируй анализ под профессию кандидата
- Если нет портфолио — не упоминай это
- tts_summary должен звучать естественно (без списков)
- НИКОГДА не используй двойные кавычки внутри строк JSON"""


# ============================================
# ПРОМПТ: Оценка соответствия вакансии
# ============================================
MATCH_SCORE_PROMPT = """Ты — строгий, но справедливый HR-специалист с 10-летним опытом найма.
Оцени соответствие кандидата вакансии. Верни ТОЛЬКО валидный JSON.

ВАЖНО: Анализируй ЛЮБУЮ профессию — IT, маркетинг, дизайн, финансы, продажи и т.д.
Адаптируй критерии под конкретную сферу.

ПРАВИЛА:
- match_score: число от 0 до 100 (процент соответствия)
- verdict: одна фраза ("Идеально подхожу", "Хорошо подхожу", "Частично подхожу", "Слабо подхожу", "Не подхожу")
- Будь честным, но поддерживающим
- Давай конкретные рекомендации

Структура ответа:
{
  "match_score": <int 0-100>,
  "verdict": "<одна фраза>",
  "match_reasons": ["<причина 1>", "<причина 2>", "<причина 3>"],
  "gap_reasons": ["<чего не хватает 1>", "<чего не хватает 2>"],
  "recommendations": ["<совет 1>", "<совет 2>", "<совет 3>"],
  "salary_estimate": "<примерная зарплата по рынку для этой позиции>",
  "tts_summary": "<короткий вердикт для озвучки на 4-5 предложений: оценка соответствия + что хорошо + чего не хватает + рекомендация>"
}

ПРАВИЛА ФОРМАТА:
- НЕ используй двойные кавычки внутри строк (используй апострофы)
- НЕ используй markdown
- tts_summary должен звучать естественно при озвучке"""


# ============================================
# ФУНКЦИЯ 1: Анализ резюме + портфолио
# ============================================
async def analyze_portfolio(
    resume_text: str,
    github_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Анализирует резюме + портфолио (GitHub или другое) и возвращает отчёт"""

    context = f"РЕЗЮМЕ КАНДИДАТА:\n{resume_text[:MAX_TEXT_LENGTH]}\n\n"

    if github_data and "error" not in github_data:
        context += (
            f"ПОРТФОЛИО/GITHUB:\n"
            f"- Публичных проектов: {github_data.get('public_repos', 0)}\n"
            f"- Всего звёзд/лайков: {github_data.get('total_stars', 0)}\n"
            f"- Основные технологии/навыки: {github_data.get('top_languages', {})}\n"
            f"- Топ проекты: {json.dumps(github_data.get('top_repos', [])[:5], ensure_ascii=False, indent=2)}\n"
        )
    else:
        context += "\nПортфолио/GitHub не предоставлено\n"

    # Универсальный вызов через роутер
    raw_text = await call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"ДАННЫЕ КАНДИДАТА:\n{context}",
        temperature=0.6,
        max_tokens=2048
    )

    if not raw_text:
        raise ValueError("Модель вернула пустой ответ")

    print(f"📝 Raw response length: {len(raw_text)}")

    raw_text = extract_json_block(raw_text)
    raw_text = fix_quotes_in_json(raw_text)

    try:
        parsed = json.loads(raw_text)
        print("✅ JSON успешно распарсен")
        return parsed
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        
        # Сначала пробуем агрессивный фикс
        fixed_json = aggressive_json_fix(raw_text)
        if fixed_json:
            print("✅ JSON восстановлен (aggressive fix)")
            return fixed_json
        
        # Потом стандартный фикс
        fixed_json = try_fix_json(raw_text)
        if fixed_json:
            print("✅ JSON восстановлен (standard fix)")
            return fixed_json

        raise ValueError(f"AI вернул невалидный JSON:\n{raw_text[:500]}")


# ============================================
# ФУНКЦИЯ 2: Генерация Cover Letter
# ============================================
async def generate_cover_letter(
    resume_text: str,
    company_name: str,
    job_description: str
) -> str:
    """Генерирует Cover Letter на основе резюме и вакансии"""
    
    system_prompt = "Ты пишешь идеальные сопроводительные письма для специалистов любых профессий."
    
    user_prompt = f"""Ты — профессиональный карьерный консультант и HR-специалист.
Напиши мотивированное сопроводительное письмо (Cover Letter) на русском языке.

ПРАВИЛА:
1. Объём: 250-350 слов.
2. Тон: уверенный, профессиональный, живой. Избегай клише.
3. Структура: Приветствие -> Почему эта компания -> Как мой опыт закрывает боли вакансии -> Призыв к действию.
4. Формат: обычный текст с разбивкой на абзацы. СТРОГО БЕЗ markdown (не используй **, #, []).
5. Адаптируй письмо под профессию кандидата (не предполагай что это IT).
6. В конце НЕ пиши "С уважением", просто закончи текст призывом к действию.

РЕЗЮМЕ КАНДИДАТА:
{resume_text[:3000]}

НАЗВАНИЕ КОМПАНИИ:
{company_name}

ОПИСАНИЕ ВАКАНСИИ:
{job_description[:2000]}"""

    letter = await call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=1024
    )
    
    # Очистка от возможных markdown остатков
    letter = letter.replace("**", "").replace("##", "").replace("#", "")
    
    if not letter or len(letter) < 50:
        raise ValueError("AI вернул слишком короткий Cover Letter")
    
    return letter


# ============================================
# ФУНКЦИЯ 3: Оценка соответствия вакансии
# ============================================
async def analyze_match_score(
    resume_text: str,
    job_description: str
) -> Dict[str, Any]:
    """Анализирует соответствие резюме вакансии"""
    
    user_prompt = f"""{MATCH_SCORE_PROMPT}

РЕЗЮМЕ КАНДИДАТА:
{resume_text[:3000]}

ОПИСАНИЕ ВАКАНСИИ:
{job_description[:2000]}"""

    raw_text = await call_llm(
        system_prompt="Ты — Senior HR. Оценивай честно и конкретно, но поддерживающе.",
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=1024
    )
    
    if not raw_text:
        raise ValueError("Модель вернула пустой ответ")
    
    print(f"📝 Match Score raw length: {len(raw_text)}")
    
    raw_text = extract_json_block(raw_text)
    raw_text = fix_quotes_in_json(raw_text)
    
    try:
        parsed = json.loads(raw_text)
        print("✅ Match Score JSON распарсен")
        return parsed
    except json.JSONDecodeError as e:
        print(f"⚠️ Match Score JSON error: {e}")
        fixed = try_fix_json(raw_text)
        if fixed:
            return fixed
        raise ValueError(f"AI вернул невалидный JSON для Match Score:\n{raw_text[:500]}")


# ============================================
# Вспомогательные функции для парсинга JSON
# ============================================

def extract_json_block(text: str) -> str:
    """Извлекает JSON блок из текста"""
    start = text.find('{')
    end = text.rfind('}')

    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text.strip()

def fix_quotes_in_json(text: str) -> str:
    """Исправляет кавычки внутри JSON строк - усиленная версия"""
    # Заменяем умные кавычки
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u00ab', '"').replace('\u00bb', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    
    # Регулярное выражение для замены двойных кавычек внутри строк
    # Находит все кавычки внутри значений и заменяет на апострофы
    import re
    
    # Разбиваем текст на части: ключи и значения
    lines = text.split('\n')
    result = []
    
    for line in lines:
        stripped = line.strip()
        
        # Пропускаем строки без кавычек
        if '"' not in stripped:
            result.append(line)
            continue
        
        # Если это строка с массивом или объектом - обрабатываем specially
        if stripped.startswith('"') and ':' in stripped:
            # Это ключ: значение
            key_end = stripped.find('":')
            if key_end != -1:
                key = stripped[:key_end + 2]
                value = stripped[key_end + 2:].rstrip(',').strip()
                
                # Если значение в кавычках - чистим его
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                    # Заменяем внутренние кавычки на апострофы
                    value = value.replace('"', "'")
                    value = f'"{value}"'
                
                result.append(key + ' ' + value + (',' if stripped.endswith(',') else ''))
            else:
                result.append(line)
        elif stripped.startswith('"') and stripped.endswith('",'):
            # Это элемент массива
            value = stripped[1:-2]
            value = value.replace('"', "'")
            result.append(f'  "{value}",')
        elif stripped.startswith('"') and stripped.endswith('"'):
            # Это элемент массива без запятой
            value = stripped[1:-1]
            value = value.replace('"', "'")
            result.append(f'  "{value}"')
        else:
            result.append(line)
    
    return '\n'.join(result)


def aggressive_json_fix(raw_text: str) -> Optional[Dict[str, Any]]:
    """Агрессивное исправление JSON - заменяет все проблемные кавычки"""
    import re
    
    # Находим все строковые значения и чистим их
    def fix_string_value(match):
        full_match = match.group(0)
        # Заменяем внутренние двойные кавычки на апострофы
        # Но только те, что не являются началом/концом строки
        parts = full_match.split('"')
        if len(parts) > 2:
            # Есть внутренние кавычки - чистим
            cleaned = parts[0] + '"'
            for i, part in enumerate(parts[1:-1]):
                cleaned += part.replace('"', "'")
                cleaned += '"'
            cleaned += parts[-1]
            return cleaned
        return full_match
    
    # Применяем регулярное выражение для исправления строк
    fixed = re.sub(r'"[^"]*"[^,}\]]*', fix_string_value, raw_text)
    
    # Пробуем распарсить
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        # Если не получилось - пробуем стандартный фикс
        return try_fix_json(raw_text)


def fix_unclosed_strings(text: str) -> str:
    """Закрывает незакрытые строки в JSON"""
    lines = text.split('\n')
    result = []

    for line in lines:
        stripped = line.rstrip()

        if '"' not in stripped:
            result.append(stripped)
            continue

        count = 0
        i = 0
        while i < len(stripped):
            if stripped[i] == '\\' and i + 1 < len(stripped):
                i += 2
                continue
            if stripped[i] == '"':
                count += 1
            i += 1

        if count % 2 == 1:
            stripped += '"'

        result.append(stripped)

    return '\n'.join(result)


def fix_unclosed_arrays(text: str) -> str:
    """Закрывает незакрытые массивы"""
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    if open_brackets > close_brackets:
        last_brace = text.rfind('}')
        if last_brace != -1:
            closing = ']' * (open_brackets - close_brackets)
            text = text[:last_brace] + closing + '\n' + text[last_brace:]
        else:
            text += ']' * (open_brackets - close_brackets)

    return text

def aggressive_json_fix(raw_text: str) -> Optional[Dict[str, Any]]:
    """Агрессивное исправление JSON - заменяет все проблемные кавычки"""
    import re
    
    # Находим все строковые значения и чистим их
    def fix_string_value(match):
        full_match = match.group(0)
        # Заменяем внутренние двойные кавычки на апострофы
        # Но только те, что не являются началом/концом строки
        parts = full_match.split('"')
        if len(parts) > 2:
            # Есть внутренние кавычки - чистим
            cleaned = parts[0] + '"'
            for i, part in enumerate(parts[1:-1]):
                cleaned += part.replace('"', "'")
                cleaned += '"'
            cleaned += parts[-1]
            return cleaned
        return full_match
    
    # Применяем регулярное выражение для исправления строк
    fixed = re.sub(r'"[^"]*"[^,}\]]*', fix_string_value, raw_text)
    
    # Пробуем распарсить
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        # Если не получилось - пробуем стандартный фикс
        return try_fix_json(raw_text)