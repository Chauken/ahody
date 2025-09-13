"""
Scraper Service for extracting content from web pages.
Integrates with BrowserService for authenticated browsing and converts results to Article models.
"""

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from fastapi import Depends
from pydantic_ai import Agent
from rich.console import Console

from app.core.browser_service import BrowserService
from app.core.models import Article, ArticleMetadata
from app.core.scraper_agent import get_article_scraping_agent

logger = logging.getLogger(__name__)
console = Console()


class ScraperService:
    """Service for scraping web content with authentication support."""

    def __init__(
        self,
        browser_service: BrowserService = Depends(BrowserService),
        scraper_agent: Agent[None, Article] = Depends(get_article_scraping_agent),
    ):
        self.browser_service = browser_service
        self.scraper_agent = scraper_agent

    async def scrape_article(self, url: str) -> Article:
        """
        Scrape an article from a URL.
        """
        try:
            article = await self.fetch_article_data(url)
        except Exception as e:
            logger.error(f"Error fetching article data: {e}")
            raise e

        try:
            # Process the article to extract relevant information
            return await self.process_article(article)
        except Exception as e:
            logger.error(f"Error scraping article with agent. Defaulting to raw content: {e}")

        return article

    async def fetch_article_data(self, url: str) -> Article:
        """
        Fetch article data from the given URL.
        """

        logger.info(f"Fetching article data from {url}")
        playwright, browser, context, page = await self.browser_service.browse_url(url)

        try:
            if not page:
                raise Exception(f"Failed to load page: {url}")

            html_content = await page.content()
            page_title = await page.title()

            cleaned_html = clean_html(html_content)
            text_content = html_to_text(cleaned_html)

            return Article(
                title=page_title,
                url=url,
                html_content=cleaned_html,
                text_content=text_content,
                date=None,
                author=None,
                metadata=ArticleMetadata(
                    page_title=page_title,
                    fetch_time=datetime.now().isoformat(),
                    word_count=len(text_content.split()),
                ),
            )

        finally:
            # Clean up browser resources
            await self.browser_service.close_browser_session(playwright, browser, context, page)

    async def process_article(self, article: Article) -> Article:
        """
        Process the article to extract relevant information.
        """
        # Use the agent to process the article
        logger.info(
            f"Processing article with agent",
            {
                "article_title": article.title,
                "article_word_count": len(article.text_content.split()),
                "html_content_size": f"{len(article.html_content)} bytes",
            },
        )

        agent_result = await self.scraper_agent.run(article.html_content)
        logger.info(f"Agent results", {"type": type(agent_result), "result": agent_result})

        if (processed_article := agent_result.data) is None:
            raise ValueError("Processed article is None")

        if isinstance(processed_article, dict):
            # If the agent returns a dictionary, extract just the fields we need
            return Article(
                title=article.title,
                url=article.url,
                html_content=article.html_content,
                text_content=processed_article.get("text_content", ""),
                date=processed_article.get("date"),
                author=processed_article.get("author"),
                metadata=article.metadata,
            )

        if isinstance(processed_article, Article):
            # The agent returns a complete Article object
            return Article.model_validate(processed_article)

        raise ValueError(f"Agent returned unexpected type: {type(processed_article)}")


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace, etc.
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove non-breaking spaces
    text = text.replace("\xa0", " ")
    return text


def html_to_text(html_content: str) -> str:
    """
    Convert HTML content to plain text using BeautifulSoup.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = clean_text(text)
    return text


def clean_html(html_content: str) -> str:
    """
    Clean and reduce HTML content to make it more manageable for processing.
    """
    if not html_content:
        return ""

    logger.info(f"Cleaning HTML content ({len(html_content)} bytes)")

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style", "iframe", "nav", "footer", "header"]):
        script.decompose()

    # Note: Selector functionality has been removed

    # Get the cleaned HTML
    cleaned_html = str(soup)
    logger.info(f"HTML cleaned and reduced to {len(cleaned_html)} bytes")
    return cleaned_html
