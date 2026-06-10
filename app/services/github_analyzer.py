import httpx
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class GitHubAnalyzer:
    """
    Анализатор GitHub профилей.
    
    Использование:
        # Без токена (публичные данные)
        analyzer = GitHubAnalyzer()
        profile = await analyzer.analyze_profile("BaltakMaksim")
        
        # С токеном (больше запросов, приватные репо)
        analyzer = GitHubAnalyzer(token="ghp_xxx")
        profile = await analyzer.analyze_profile("BaltakMaksim")
    """
    
    BASE_URL = "https://api.github.com"
    USER_AGENT = "Portfolio-Roaster/1.0"
    
    def __init__(self, token: Optional[str] = None):
        """
        Инициализация анализатора.
        
        Args:
            token: GitHub Personal Access Token (опционально)
        """
        self.token = token
        self.headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    async def analyze_profile(self, username: str) -> Dict[str, Any]:
        """
        Анализирует GitHub профиль и возвращает структурированные данные.
        
        Args:
            username: GitHub username
            
        Returns:
            Словарь с данными профиля или {"error": "..."} при ошибке
        """
        logger.info(f"🔍 Анализ GitHub профиля: {username}")
        
        try:
            # Параллельные запросы для скорости
            async with httpx.AsyncClient(
                timeout=30.0,
                headers=self.headers,
                base_url=self.BASE_URL
            ) as client:
                user_data = await self._fetch_user_info(client, username)
                if "error" in user_data:
                    return user_data
                
                # Параллельно запрашиваем репо и события
                repos, events = await self._fetch_repos_and_events(client, username)
                
                # Анализируем данные
                analysis = self._analyze_data(username, user_data, repos, events)
                
                logger.info(f"✅ Профиль {username} проанализирован")
                logger.debug(f"Репозиториев: {analysis['public_repos']}, Звёзд: {analysis['total_stars']}")
                
                return analysis
                
        except httpx.TimeoutException:
            logger.error(f"⏱️ Таймаут при анализе {username}")
            return {"error": "Таймаут запроса к GitHub API"}
        except Exception as e:
            logger.error(f"❌ Ошибка анализа {username}: {type(e).__name__}: {str(e)}")
            return {"error": f"Ошибка анализа: {str(e)}"}
    
    async def _fetch_user_info(self, client: httpx.AsyncClient, username: str) -> Dict[str, Any]:
        """Получает основную информацию о пользователе."""
        response = await client.get(f"/users/{username}")
        
        if response.status_code == 404:
            logger.warning(f"⚠️ Профиль {username} не найден")
            return {"error": "Профиль не найден"}
        
        if response.status_code != 200:
            logger.error(f"❌ GitHub API ошибка: {response.status_code}")
            return {"error": f"GitHub API вернул статус {response.status_code}"}
        
        return response.json()
    
    async def _fetch_repos_and_events(
        self,
        client: httpx.AsyncClient,
        username: str
    ) -> tuple[List[Dict], List[Dict]]:
        """Параллельно получает репозитории и события."""
        # Параллельные запросы через asyncio.gather
        import asyncio
        
        repos_task = self._fetch_repos(client, username)
        events_task = self._fetch_events(client, username)
        
        repos, events = await asyncio.gather(repos_task, events_task)
        
        return repos, events
    
    async def _fetch_repos(self, client: httpx.AsyncClient, username: str) -> List[Dict]:
        """Получает репозитории пользователя."""
        response = await client.get(
            f"/users/{username}/repos",
            params={"sort": "updated", "per_page": 10}
        )
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Не удалось получить репо {username}: {response.status_code}")
            return []
        
        return response.json()
    
    async def _fetch_events(self, client: httpx.AsyncClient, username: str) -> List[Dict]:
        """Получает публичные события пользователя."""
        response = await client.get(
            f"/users/{username}/events/public",
            params={"per_page": 100}
        )
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Не удалось получить события {username}: {response.status_code}")
            return []
        
        return response.json()
    
    def _analyze_data(
        self,
        username: str,
        user_data: Dict[str, Any],
        repos: List[Dict],
        events: List[Dict]
    ) -> Dict[str, Any]:
        """Анализирует полученные данные и формирует итоговый отчёт."""
        
        # Подсчёт коммитов
        commits_count = len([e for e in events if e.get("type") == "PushEvent"])
        
        # Анализ языков и статистики
        languages = {}
        total_stars = 0
        total_forks = 0
        
        for repo in repos:
            total_stars += repo.get("stargazers_count", 0)
            total_forks += repo.get("forks_count", 0)
            
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        # Топ языков (отсортированные по использованию)
        top_languages = dict(
            sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        # Топ репозиториев
        top_repos = [
            {
                "name": r["name"],
                "description": r.get("description") or "Нет описания",
                "language": r.get("language") or "Unknown",
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "url": r.get("html_url", "")
            }
            for r in repos[:5]
        ]
        
        return {
            "username": username,
            "name": user_data.get("name", ""),
            "bio": user_data.get("bio", ""),
            "avatar_url": user_data.get("avatar_url", ""),
            "profile_url": user_data.get("html_url", ""),
            "public_repos": user_data.get("public_repos", 0),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "recent_commits": commits_count,
            "top_languages": top_languages,
            "top_repos": top_repos,
        }