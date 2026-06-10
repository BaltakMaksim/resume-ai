"""
Утилиты для безопасного парсинга JSON ответов от LLM.
"""

import json
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class JSONParser:
    """Безопасный парсер JSON с многоуровневым фиксом."""

    @staticmethod
    def parse_safely(raw_text: str, context: str = "") -> Dict[str, Any]:
        """Пытается распарсить JSON с несколькими уровнями фикса."""
        if not raw_text:
            raise ValueError(f"{context}: модель вернула пустой ответ")

        # Шаг 1: извлекаем JSON-блок
        text = JSONParser.extract_json_block(raw_text)

        # Шаг 2: чистим кавычки
        text = JSONParser.fix_quotes(text)

        # Шаг 3: пробуем распарсить напрямую
        try:
            parsed = json.loads(text)
            logger.info(f"✅ {context}: JSON распарсен с первой попытки")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ {context}: первичный парсинг не удался — {e}")

        # Шаг 4: агрессивный фикс
        fixed = JSONParser.aggressive_fix(text)
        if fixed:
            logger.info(f"✅ {context}: JSON восстановлен (aggressive fix)")
            return fixed

        # Шаг 5: закрытие незакрытых скобок/строк
        fixed = JSONParser.structural_fix(text)
        try:
            parsed = json.loads(fixed)
            logger.info(f"✅ {context}: JSON восстановлен (structural fix)")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"❌ {context}: все попытки парсинга провалились — {e}")
            raise ValueError(f"AI вернул невалидный JSON:\n{text[:500]}")

    @staticmethod
    def extract_json_block(text: str) -> str:
        """Извлекает JSON-блок из текста (убирает markdown, преамбулы)."""
        # Убираем markdown-обёртку ```json ... ```
        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if md_match:
            return md_match.group(1).strip()

        # Иначе ищем первую { и последнюю }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return text[start : end + 1]

        return text.strip()

    @staticmethod
    def fix_quotes(text: str) -> str:
        """Заменяет умные кавычки на стандартные."""
        replacements = {
            "\u201c": '"', "\u201d": '"',  # " "
            "\u00ab": '"', "\u00bb": '"',  # « »
            "\u2018": "'", "\u2019": "'",  # ‘ ’
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def aggressive_fix(text: str) -> Optional[Dict[str, Any]]:
        """Пытается исправить внутренние кавычки в строковых значениях."""
        # Находим строковые значения и экранируем внутренние кавычки
        def escape_inner_quotes(match: re.Match) -> str:
            s = match.group(0)
            inner = s[1:-1]
            # Экранируем кавычки, которые не являются escaped
            inner = re.sub(r'(?<!\\)"', '\\"', inner)
            return f'"{inner}"'

        # Применяем к значениям после ":"
        fixed = re.sub(r'(?<=:\s)"[^"\n]*"(?=\s*[,}\]])', escape_inner_quotes, text)
        # И к элементам массивов
        fixed = re.sub(r'(?<=[\[,]\s)"[^"\n]*"(?=\s*[,}\]])', escape_inner_quotes, fixed)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def structural_fix(text: str) -> str:
        """Закрывает незакрытые строки, массивы и объекты."""
        # Закрываем незакрытые строки
        lines = text.split("\n")
        fixed_lines = []
        for line in lines:
            stripped = line.rstrip()
            if '"' not in stripped:
                fixed_lines.append(stripped)
                continue

            # Считаем неэкранированные кавычки
            count = 0
            i = 0
            while i < len(stripped):
                if stripped[i] == "\\" and i + 1 < len(stripped):
                    i += 2
                    continue
                if stripped[i] == '"':
                    count += 1
                i += 1

            if count % 2 == 1:
                stripped += '"'
            fixed_lines.append(stripped)

        text = "\n".join(fixed_lines)

        # Закрываем незакрытые массивы и объекты
        open_sq = text.count("[") - text.count("]")
        open_cu = text.count("{") - text.count("}")
        if open_sq > 0:
            text += "]" * open_sq
        if open_cu > 0:
            text += "}" * open_cu

        return text