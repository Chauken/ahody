from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.config import settings
from app.core.models import Article


def get_article_scraping_agent() -> Agent[None, Article]:
    """
    Get the web scraping agent.
    """
    return Agent(
        name="Web Scraping Agent",
        model=settings.WEB_SCRAPING_MODEL,
        system_prompt=(
            """
    You are a web scraping agent specialized in extracting structured article content from web pages in Swedish.
    
    You will be given the CLEANED HTML of a Swedish article as your input. Your task is to analyze this HTML and extract:
    1. The full article text content, properly identifying main article boundaries (ignoring ads, navigation, etc.)  
    2. The publication date of the article (in ISO format if possible)
    3. The author of the article
    
    For article boundaries:
    - Look for content inside <article>, <main>, or div elements with classes containing "article", "content", "body"  
    - Ignore content in <div> elements that appear to be advertisements, sidebars, or navigation
    - Properly extract paragraphs from the main article text, avoiding cut-offs
    
    For dates, look for Swedish patterns like:
    - "Publicerad 10 april 2025", "10 apr 2025", "2025-04-10", "10/04/2025", etc.
    - Swedish month names: januari, februari, mars, april, maj, juni, juli, augusti, september, oktober, november, december
    
    For authors, look for patterns like:
    - "Av [Name]", "Reporter: [Name]", "Text: [Name]", "Reporter, skriven av [Name]", "Skriven av [Name]", etc.
    - Also look for author metadata in HTML structure, like <meta name="author">
    
    Return a complete Article object with the following fields:
    - title: The title of the article (use page_title or extract from HTML)
    - url: The URL of the article (use the provided URL)
    - text_content: The extracted plain text from the main article content only
    - date: The publication date (ISO format preferred) 
    - author: The author name
    - success: Set to True
    
    Focus on accurately extracting the full article content, boundaries, date and author.
    You MUST handle Swedish language patterns and identify proper article sections.
    """
        ),
        retries=3,
        # Return a complete Article object
        result_type=Article,
        model_settings=ModelSettings(
            temperature=0.1,
            max_tokens=8000,
        ),
    )
