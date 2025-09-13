from fastapi import APIRouter

from app.api.routes import article, sources

api_router = APIRouter()
api_router.include_router(article.router)
api_router.include_router(sources.router)
