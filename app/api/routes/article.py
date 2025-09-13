from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.models import Article
from app.core.scraper_service import ScraperService

router = APIRouter()


class ScrapeArticleRequest(BaseModel):
    url: str


class ScrapeArticleResponse(BaseModel):
    title: str
    url: str
    html_content: str
    text_content: str
    date: str | None = None
    author: str | None = None


@router.post("/scrape-article")
async def scrape_article(
    request: ScrapeArticleRequest, scraper_service: ScraperService = Depends(ScraperService)
) -> ScrapeArticleResponse:
    """
    Scrape the article from the given URL.
    """
    if not request.url.startswith("http"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    try:
        # Use the scraper service to fetch and process the article
        article: Article = await scraper_service.scrape_article(request.url)

        # Convert Article model to ScrapeArticleResponse
        return ScrapeArticleResponse(
            title=article.title,
            url=article.url,
            html_content=article.html_content,
            text_content=article.text_content,
            date=article.date,
            author=article.author,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scraping article: {str(e)}",
        )
