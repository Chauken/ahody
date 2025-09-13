from fastapi import APIRouter

from app.api.routes import article, sources, general_scrape

api_router = APIRouter()
api_router.include_router(article.router)
api_router.include_router(sources.router)
api_router.include_router(general_scrape.router)
