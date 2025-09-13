from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import logging
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy
from typing import List
import json
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class ArticleUrl(BaseModel):
    url: str
    title: str | None = None


class GeneralScrapeRequest(BaseModel):
    url: str


class GeneralScrapeResponse(BaseModel):
    source_url: str
    article_urls: List[ArticleUrl]
    total_articles: int


class ArticleList(BaseModel):
    articles: List[ArticleUrl]


@router.post("/general-scrape")
async def general_scrape(request: GeneralScrapeRequest) -> GeneralScrapeResponse:
    """
    Perform general scraping to extract article URLs from a news website using crawl4ai.
    Returns a list of article URLs without scraping the full content.
    """
    if not request.url.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL - must start with http or https"
        )
    
    try:
        logger.info(f"Starting crawl4ai scrape for URL: {request.url}")
        
        # LLM extraction strategy with proper configuration
        llm_strategy = LLMExtractionStrategy(
            llmConfig=LLMConfig(
                provider="openai/gpt-4o-mini",
                api_token=settings.OPENAI_API_KEY
            ),
            schema=ArticleList.model_json_schema(),
            extraction_type="schema",
            instruction="""
            Extract all news article links from this webpage. Look for:
            1. Links to individual news articles (not category pages or navigation)
            2. Article titles associated with those links
            3. Only include actual news content, not ads, navigation, or footer links
            4. Convert relative URLs to absolute URLs
            
            Return a JSON object with an 'articles' array containing objects with 'url' and 'title' fields.
            """,
            chunk_token_threshold=1400,
            apply_chunking=True,
            input_format="html",
            extra_args={"temperature": 0.1, "max_tokens": 2000}
        )
        
        crawl_config = CrawlerRunConfig(
            extraction_strategy=llm_strategy,
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            result = await crawler.arun(url=request.url, config=crawl_config)
            
            if result.success:
                logger.info("Crawl4ai extraction successful")
                logger.info(f"Raw LLM response: {result.extracted_content}")
                
                # Parse the extracted data
                try:
                    extracted_data = json.loads(result.extracted_content)
                    
                    # Handle chunked responses - extracted_data is a list of chunks
                    all_articles = []
                    if isinstance(extracted_data, list):
                        # Multiple chunks returned due to chunking
                        for chunk in extracted_data:
                            if isinstance(chunk, dict) and "articles" in chunk:
                                chunk_articles = chunk.get("articles", [])
                                all_articles.extend(chunk_articles)
                    elif isinstance(extracted_data, dict):
                        # Single response
                        all_articles = extracted_data.get("articles", [])
                    
                    # Remove duplicates based on URL
                    seen_urls = set()
                    unique_articles = []
                    for article in all_articles:
                        url = article.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            unique_articles.append(article)
                    
                    article_urls = []
                    for article in unique_articles:
                        url = article.get("url", "")
                        title = article.get("title", "")
                        
                        # Ensure URL is absolute
                        if url.startswith("/"):
                            from urllib.parse import urljoin
                            url = urljoin(request.url, url)
                        
                        if url and url.startswith("http"):
                            article_urls.append(ArticleUrl(
                                url=url,
                                title=title if title else None
                            ))
                    
                    logger.info(f"Found {len(article_urls)} unique article URLs using crawl4ai")
                    
                    # Show token usage for monitoring
                    llm_strategy.show_usage()
                    
                    return GeneralScrapeResponse(
                        source_url=request.url,
                        article_urls=article_urls,
                        total_articles=len(article_urls)
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted content: {e}")
                    logger.error(f"Raw content: {result.extracted_content}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to parse extracted article data"
                    )
            else:
                logger.error(f"Crawl4ai failed: {result.error_message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Crawling failed: {result.error_message}"
                )
        
    except Exception as e:
        logger.error(f"General scraping error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing general scraping: {str(e)}"
        )
