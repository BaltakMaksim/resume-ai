import json
import re
import httpx
from typing import Optional, Dict, Any
from app.config import MAX_TEXT_LENGTH, MODEL_NAME, OLLAMA_URL, REQUEST_TIMEOUT

MATCH_SCORE_PROMPT = """Ты — строгий Senior HR с 15-летним опытом найма в IT.
Оцени соответствие кандидата вакансии. Верни ТОЛЬКО валидный JSON.

ПРАВИЛА:
- match_score: число от 0 до 100 (процент соответствия)
- verdict: одна фраза ("Идеально подхожу", "Хорошо подхожу", "Частично подхожу", "Слабо подхожу", "Не подхожу")
- НЕ используй двойные кавычки внутри строк (используй апострофы)
- НЕ используй markdown

Структура ответа:
{
  "match_score": <int 0-100>,
  "verdict": "<одна фраза>",
  "match_reasons": ["<причина 1>", "<причина 2>", "<причина 3>"],
  "gap_reasons": ["<чего не хватает 1>", "<чего не хватает 2>"],
  "recommendations": ["<совет 1>", "<совет 2>", "<совет 3>"],
  "salary_estimate": "<примерная зарплата по рынку>",
  "tts_summary": "<короткий вердикт для озвучки на 2-3 предложения>"
}"""

SYSTEM_PROMPT = """Ты — строгий Senior HR и Tech Lead с 15-летним опытом найма в FAANG.
Проанализируй данные разработчика. Верни ТОЛЬКО валидный JSON.

ПРАВИЛА ОЦЕНИВАНИЯ:
- resume_score: ВСЕГДА заполняй (оценка резюме от 1 до 10)
- github_score: заполняй ТОЛЬКО если есть данные GitHub, иначе null
- overall_score: среднее между resume_score и github_score (если есть оба), или равно resume_score

ПРАВИЛА ФОРМАТА:
- НЕ используй двойные кавычки внутри строк (используй апострофы)
- НЕ используй markdown обёртки

Структура ответа:
{
  "overall_score": <int 1-10>,
  "resume_score": <int 1-10 - ВСЕГДА ОБЯЗАТЕЛЬНО>,
  "github_score": <int 1-10 или null если нет GitHub>,
  "roast": "<едкая фраза, макс 100 символов>",
  "strengths": ["<сильная сторона 1>", "<сильная сторона 2>"],
  "critical_errors": ["<ошибка 1>", "<ошибка 2>"],
  "missing_keywords": ["<keyword 1>", "<keyword 2>"],
  "advice_for_offer": "<конкретный совет>",
  "tech_stack_analysis": "<краткий анализ>",
  "tts_summary": "<текст на 2-3 предложения для озвучки>"
}"""


async def analyze_portfolio(
    resume_text: str,
    github_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Анализирует резюме + GitHub и возвращает отчёт"""

    context = f"РЕЗЮМЕ:\n{resume_text[:MAX_TEXT_LENGTH]}\n\n"

    if github_data and "error" not in github_data:
        context += (
            f"GITHUB:\n"
            f"- Репозиториев: {github_data.get('public_repos', 0)}\n"
            f"- Звёзд: {github_data.get('total_stars', 0)}\n"
            f"- Языки: {github_data.get('top_languages', {})}\n"
            f"- Проекты: {json.dumps(github_data.get('top_repos', [])[:3], ensure_ascii=False)}\n"
        )
    else:
        context += "\nGitHub не предоставлен\n"

    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"ДАННЫЕ:\n{context}"}
        ],
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "overall_score": {"type": "integer"},
                "resume_score": {"type": "integer"},
                "github_score": {"type": "integer"},
                "roast": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "critical_errors": {"type": "array", "items": {"type": "string"}},
                "missing_keywords": {"type": "array", "items": {"type": "string"}},
                "advice_for_offer": {"type": "string"},
                "tech_stack_analysis": {"type": "string"},
                "tts_summary": {"type": "string"}
            },
            "required": [
                "overall_score", "roast", "strengths",
                "critical_errors", "advice_for_offer", "tts_summary"
            ]
        },
        "options": {
            "temperature": 0.7,
            "num_predict": -1,
            "num_ctx": 16384,
            "top_p": 0.9,
            "top_k": 40
        }
    }

    chat_url = str(OLLAMA_URL).replace("/api/generate", "/api/chat")

    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(chat_url, json=payload)
        response.raise_for_status()
        result: Dict[str, Any] = response.json()
    
    print(result)
    raw_text: str = result.get("message", {}).get("content", "").strip()

    if not raw_text:
        raise ValueError("Модель вернула пустой ответ")

    print(f"📝 Raw response length: {len(raw_text)}")
    print(f" Done: {result.get('done', False)}")

    raw_text = extract_json_block(raw_text)
    raw_text = fix_quotes_in_json(raw_text)

    try:
        parsed = json.loads(raw_text)
        print("✅ JSON успешно распарсен")
        return parsed
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        print(f" First 500 chars: {raw_text[:500]}")
        
        fixed_json: Optional[Dict[str, Any]] = try_fix_json(raw_text)
        if fixed_json:
            print("✅ JSON восстановлен")
            return fixed_json

        raise ValueError(f"AI вернул невалидный JSON:\n{raw_text[:500]}")


async def generate_cover_letter(
    resume_text: str,
    company_name: str,
    job_description: str
) -> str:
    """Генерирует Cover Letter на основе резюме и вакансии"""
    
    prompt = f"""Ты — профессиональный HR-специалист и карьерный консультант.
Напиши мотивированное сопроводительное письмо (Cover Letter) на русском языке.

ПРАВИЛА:
1. Объём: 250-350 слов.
2. Тон: уверенный, профессиональный, живой. Избегай клише.
3. Структура: Приветствие -> Почему эта компания -> Как мой опыт закрывает боли вакансии -> Призыв к действию.
4. Формат: обычный текст с разбивкой на абзацы. СТРОГО БЕЗ markdown (не используй **, #, []).
5. В конце НЕ пиши "С уважением", просто закончи текст призывом к действию.

РЕЗЮМЕ КАНДИДАТА:
{resume_text[:3000]}

НАЗВАНИЕ КОМПАНИИ:
{company_name}

ОПИСАНИЕ ВАКАНСИИ:
{job_description[:2000]}"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты пишешь идеальные Cover Letter для IT-специалистов."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 2048,
            "num_ctx": 4096
        }
    }
    
    chat_url = str(OLLAMA_URL).replace("/api/generate", "/api/chat")
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(chat_url, json=payload)
        response.raise_for_status()
        result = response.json()
    
    letter = result.get("message", {}).get("content", "").strip()
    
    # Очистка от возможных markdown остатков
    letter = letter.replace("**", "").replace("##", "").replace("#", "")
    
    return letter

async def analyze_match_score(
    resume_text: str,
    job_description: str
) -> Dict[str, Any]:
    """Анализирует соответствие резюме вакансии"""
    
    prompt = f"""{MATCH_SCORE_PROMPT}

РЕЗЮМЕ КАНДИДАТА:
{resume_text[:3000]}

ОПИСАНИЕ ВАКАНСИИ:
{job_description[:2000]}"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — Senior HR. Оценивай честно и конкретно."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "match_score": {"type": "integer"},
                "verdict": {"type": "string"},
                "match_reasons": {"type": "array", "items": {"type": "string"}},
                "gap_reasons": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "salary_estimate": {"type": "string"},
                "tts_summary": {"type": "string"}
            },
            "required": ["match_score", "verdict", "match_reasons", "gap_reasons", "tts_summary"]
        },
        "options": {
            "temperature": 0.5,
            "num_predict": 2048,
            "num_ctx": 8192
        }
    }
    
    chat_url = str(OLLAMA_URL).replace("/api/generate", "/api/chat")
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(chat_url, json=payload)
        response.raise_for_status()
        result = response.json()
    
    raw_text = result.get("message", {}).get("content", "").strip()
    
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

def extract_json_block(text: str) -> str:
    """Извлекает JSON блок из текста"""
    start = text.find('{')
    end = text.rfind('}')

    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text.strip()


def fix_quotes_in_json(text: str) -> str:
    """Исправляет кавычки внутри JSON строк"""
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u00ab', '"').replace('\u00bb', '"')
    text = re.sub(r"'([^']*)'", r'"\1"', text)
    return text


def try_fix_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Пытается восстановить обрезанный JSON"""
    fixed = fix_unclosed_arrays(raw_text)
    fixed = fix_unclosed_strings(fixed)
    
    last_brace = fixed.rfind('}')
    if last_brace != -1:
        fixed = fixed[:last_brace + 1]

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


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



