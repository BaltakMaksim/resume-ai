import httpx
import logging
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HtmlParser:
    """
    Парсер HTML-страниц для извлечения текста.
    
    Использование:
        # С настройками по умолчанию
        parser = HtmlParser()
        text = await parser.parse_page("https://example.com")
        
        # С кастомными настройками
        parser = HtmlParser(timeout=30.0, max_length=5000)
        text = await parser.parse_page("https://example.com")
        
        # Парсинг из HTML-строки (без запроса)
        text = HtmlParser.parse_html("<html><body>Привет</body></html>")
    """
    
    # Константы класса
    DEFAULT_TIMEOUT = 10.0
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    DEFAULT_MAX_LENGTH = 3000
    
    # Элементы, которые удаляем перед извлечением текста
    REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]
    
    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        max_length: int = DEFAULT_MAX_LENGTH
    ):
        """
        Инициализация парсера.
        
        Args:
            timeout: Таймаут HTTP-запроса в секундах
            user_agent: User-Agent для запросов
            max_length: Максимальная длина извлекаемого текста
        """
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_length = max_length
        
        logger.info(
            f"🌐 HtmlParser инициализирован: timeout={timeout}s, max_length={max_length}"
        )
    
    async def parse_page(self, url: str, max_length: Optional[int] = None) -> str:
        """
        Загружает HTML-страницу по URL и извлекает текст.
        
        Args:
            url: URL страницы для парсинга
            max_length: Опционально переопределить максимальную длину текста
            
        Returns:
            Извлечённый текст (обрезанный до max_length)
            
        Raises:
            ValueError: Если URL невалидный
            httpx.HTTPStatusError: Если HTTP-запрос вернул ошибку
            httpx.TimeoutException: Если истёк таймаут
        """
        # Валидация URL
        if not self._is_valid_url(url):
            logger.error(f"❌ Невалидный URL: {url}")
            raise ValueError(f"Невалидный URL: {url}")
        
        actual_max_length = max_length if max_length is not None else self.max_length
        
        logger.info(f"📥 Парсинг страницы: {url}")
        logger.debug(f"Таймаут: {self.timeout}s, Max length: {actual_max_length}")
        
        try:
            # Загружаем HTML
            html_content = await self._fetch_html(url)
            
            # Парсим и извлекаем текст
            text = self.parse_html(html_content, max_length=actual_max_length)
            
            logger.info(f"✅ Текст извлечён: {len(text)} символов")
            logger.debug(f"Текст: {text[:200]}...")
            
            return text
            
        except httpx.TimeoutException:
            logger.error(f"⏱️ Таймаут при загрузке {url}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP ошибка {e.response.status_code} для {url}")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {url}: {type(e).__name__}: {str(e)}")
            raise
    
    async def _fetch_html(self, url: str) -> str:
        """Загружает HTML-контент страницы."""
        headers = {"User-Agent": self.user_agent}
        
        logger.debug(f"📤 GET запрос к {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            
            logger.debug(f"✅ Ответ получен: {response.status_code}, {len(response.text)} байт")
            return response.text
    
    @staticmethod
    def parse_html(html_content: str, max_length: int = 3000) -> str:
        """
        Парсит HTML-строку и извлекает текст (без HTTP-запроса).
        
        Args:
            html_content: HTML-контент для парсинга
            max_length: Максимальная длина извлекаемого текста
            
        Returns:
            Извлечённый текст
        """
        if not html_content or not html_content.strip():
            logger.warning("⚠️ Пустой HTML-контент")
            return ""
        
        logger.debug(f"🔍 Парсинг HTML: {len(html_content)} байт")
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Удаляем ненужные элементы
            HtmlParser._clean_soup(soup)
            
            # Извлекаем текст
            text = soup.get_text(separator=" ", strip=True)
            
            # Нормализуем пробелы
            text = HtmlParser._normalize_whitespace(text)
            
            # Обрезаем до максимальной длины
            if len(text) > max_length:
                text = text[:max_length]
                logger.debug(f"✂️ Текст обрезан до {max_length} символов")
            
            logger.debug(f"✅ Извлечено: {len(text)} символов")
            return text
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга HTML: {type(e).__name__}: {str(e)}")
            raise
    
    @staticmethod
    def _clean_soup(soup: BeautifulSoup) -> None:
        """Удаляет ненужные элементы из BeautifulSoup объекта."""
        for tag_name in HtmlParser.REMOVE_TAGS:
            for element in soup.find_all(tag_name):
                element.extract()
        
        logger.debug(f"🧹 Удалены теги: {', '.join(HtmlParser.REMOVE_TAGS)}")
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Нормализует пробелы в тексте."""
        # Заменяем множественные пробелы на одиночные
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Проверяет валидность URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @classmethod
    async def quick_parse(cls, url: str, max_length: int = 3000) -> str:
        """
        Быстрый парсинг без создания экземпляра класса.
        
        Args:
            url: URL страницы
            max_length: Максимальная длина текста
            
        Returns:
            Извлечённый текст
        """
        parser = cls(max_length=max_length)
        return await parser.parse_page(url)