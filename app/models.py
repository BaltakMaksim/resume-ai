from pydantic import BaseModel, HttpUrl

class UrlRequest(BaseModel):
    """Модель запроса для анализа портфолио."""
    url: HttpUrl
    
class PortfolioAnalysis(BaseModel):
    """Ответ ИИ"""
    scope: str
    roastr: str
    errors: list[str]
    advice: str