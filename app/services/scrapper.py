import httpx
from bs4 import BeautifulSoup
from app.config import MAX_TEXT_LENGTH

async def scape_url(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(str(url), headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text,"html.parser")
        # Удаляем ненужные элементы
        for element in soup(["script","style","nav","footer","header"]):
            element.extract()
          # Извлекаем текст и обрезаем
        text = soup.get_text(separator=" ", strip=True)
        return text[:MAX_TEXT_LENGTH]