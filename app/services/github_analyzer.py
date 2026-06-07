import httpx
from typing import Optional, Dict, Any

async def analyze_github_profile(username: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Анализирует GitHub профиль и возвращает структурированные данные"""
    
    headers = {"User-Agent": "Portfolio-Roaster/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Основная информация
        user_response = await client.get(f"https://api.github.com/users/{username}")
        if user_response.status_code != 200:
            return {"error": "Профиль не найден"}
        
        user_data = user_response.json()
        
        # Репозитории
        repos_response = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 10}
        )
        repos = repos_response.json() if repos_response.status_code == 200 else []
        
        # Коммиты за последний год
        events_response = await client.get(
            f"https://api.github.com/users/{username}/events/public",
            params={"per_page": 100}
        )
        events = events_response.json() if events_response.status_code == 200 else []
        
        # Подсчитываем коммиты
        commits_count = len([e for e in events if e["type"] == "PushEvent"])
        
        # Анализируем языки и звёзды
        languages = {}
        total_stars = 0
        total_forks = 0
        
        for repo in repos:
            total_stars += repo.get("stargazers_count", 0)
            total_forks += repo.get("forks_count", 0)
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "username": username,
            "name": user_data.get("name", ""),
            "bio": user_data.get("bio", ""),
            "public_repos": user_data.get("public_repos", 0),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "recent_commits": commits_count,
            "top_languages": dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]),
            "top_repos": [
                {
                    "name": r["name"],
                    "description": r["description"] or "Нет описания",
                    "language": r["language"] or "Unknown",
                    "stars": r["stargazers_count"],
                    "url": r["html_url"]
                }
                for r in repos[:5]
            ]
        }