from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.router import api
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)


logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

app = FastAPI(
    title="Portfolio Roaster",
    description="ИИ-агент, который разнесёт твоё портфолио в пух и прах (но по делу)",
    version="2.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты API
app.include_router(api.router)

# Раздача статики (фронтенд)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/api/docs")
async def docs_redirect():
    """Редирект на Swagger UI"""
    return {"docs": "/docs", "redoc": "/redoc"}
    