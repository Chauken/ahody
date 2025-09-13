#!/usr/bin/env python3
"""
Simple test script to crawl URLs and extract basic content using Adaptive Crawling.
"""

import asyncio
import json
import re
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig
from pydantic import BaseModel
from bs4 import BeautifulSoup


class ScrapeArticleResponse(BaseModel):
    title: str
    url: str
    text_content: str
    date: str | None = None
    author: str | None = None


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace, etc."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove non-breaking spaces
    text = text.replace("\xa0", " ")
    return text


def html_to_text(html_content: str) -> str:
    """Convert HTML content to plain text using BeautifulSoup."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = clean_text(text)
    return text


def clean_html(html_content: str) -> str:
    """Clean and reduce HTML content to make it more manageable for processing."""
    if not html_content:
        return ""
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "iframe", "nav", "footer", "header"]):
        script.decompose()
    
    # Remove ads, social media, and other non-content elements
    for element in soup(["aside", ".ad", ".advertisement", ".social", ".share", ".comments"]):
        element.decompose()
    
    # Try to find main article content
    main_content = None
    
    # Look for common article containers
    article_selectors = [
        "article",
        ".article-content",
        ".article-body", 
        ".content",
        ".post-content",
        ".entry-content",
        "main"
    ]
    
    for selector in article_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    # If we found main content, use only that
    if main_content:
        cleaned_html = str(main_content)
    else:
        # Fallback: remove common non-content elements
        for element in soup(["nav", "header", "footer", ".menu", ".navigation"]):
            element.decompose()
        cleaned_html = str(soup)
    
    return cleaned_html


def extract_date_from_html(html_content: str) -> str | None:
    """Extract publication date from HTML content."""
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Look for common date patterns
    date_selectors = [
        'time[datetime]',
        '.date',
        '.publish-date',
        '.published',
        '.article-date',
        '[data-date]',
        '.timestamp'
    ]
    
    for selector in date_selectors:
        date_element = soup.select_one(selector)
        if date_element:
            # Try to get datetime attribute first
            date_value = date_element.get('datetime') or date_element.get('data-date')
            if date_value:
                return date_value
            # Fallback to text content
            date_text = date_element.get_text(strip=True)
            if date_text:
                return date_text
    
    # Look for meta tags with date information
    meta_selectors = [
        'meta[property="article:published_time"]',
        'meta[name="publish-date"]',
        'meta[name="date"]',
        'meta[property="og:updated_time"]'
    ]
    
    for selector in meta_selectors:
        meta_element = soup.select_one(selector)
        if meta_element:
            content = meta_element.get('content')
            if content:
                return content
    
    return None


def extract_author_from_html(html_content: str) -> str | None:
    """Extract author information from HTML content."""
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Look for common author patterns
    author_selectors = [
        '.author',
        '.byline',
        '.writer',
        '.journalist',
        '.article-author',
        '[rel="author"]',
        '.by-author'
    ]
    
    for selector in author_selectors:
        author_element = soup.select_one(selector)
        if author_element:
            author_text = author_element.get_text(strip=True)
            if author_text:
                # Clean up common prefixes
                author_text = re.sub(r'^(av|by|author:?)\s*', '', author_text, flags=re.IGNORECASE)
                return author_text
    
    # Look for meta tags with author information
    meta_selectors = [
        'meta[name="author"]',
        'meta[property="article:author"]',
        'meta[name="byl"]'
    ]
    
    for selector in meta_selectors:
        meta_element = soup.select_one(selector)
        if meta_element:
            content = meta_element.get('content')
            if content:
                return content
    
    return None


async def adaptive_crawl_news_site(site_url: str, site_name: str, max_articles: int = 5) -> list[ScrapeArticleResponse]:
    """Use Adaptive Crawling to intelligently discover and extract news articles."""
    print(f"🧠 Adaptive crawling: {site_name}")
    
    # Configure adaptive crawler for news content
    config = AdaptiveConfig(
        strategy="statistical",  # Fast and efficient for news
        confidence_threshold=0.7,  # Good balance for news coverage
        max_pages=max_articles * 2,  # Allow some exploration
        top_k_links=3,  # Follow top 3 most relevant links per page
        min_gain_threshold=0.05  # Continue if gaining new information
    )
    
    articles = []
    
    async with AsyncWebCrawler() as crawler:
        adaptive = AdaptiveCrawler(crawler, config)
        
        # Define news-specific queries based on the site
        if 'aftonbladet' in site_url:
            query = "breaking news latest articles nyheter senaste"
        elif 'polisen' in site_url:
            query = "police news incidents reports händelser"
        else:
            query = "latest news articles today"
        
        try:
            # Use adaptive crawling to find relevant content
            result = await adaptive.digest(
                start_url=site_url,
                query=query
            )
            
            # Print crawling statistics
            print(f"  📊 Confidence: {result.confidence:.2%}")
            print(f"  📄 Pages crawled: {len(result.pages)}")
            adaptive.print_stats(detailed=False)
            
            # Get the most relevant pages
            relevant_pages = adaptive.get_relevant_content(top_k=max_articles)
            
            for page_data in relevant_pages:
                url = page_data['url']
                content = page_data['content']
                score = page_data['score']
                
                print(f"  📄 Processing: {url} (relevance: {score:.2%})")
                
                # Extract metadata from the page content
                date = extract_date_from_html(content)
                author = extract_author_from_html(content)
                text_content = html_to_text(clean_html(content))
                
                # Extract title from content or use URL-based fallback
                soup = BeautifulSoup(content, "html.parser")
                title_elem = soup.find('title') or soup.find('h1')
                title = title_elem.get_text(strip=True) if title_elem else f"Article from {site_name}"
                
                article = ScrapeArticleResponse(
                    title=title,
                    url=url,
                    text_content=text_content,
                    date=date,
                    author=author
                )
                
                articles.append(article)
                
                print(f"    ✅ Article length: {len(text_content)} chars")
                if date:
                    print(f"    📅 Date found: {date}")
                if author:
                    print(f"    ✍️  Author found: {author}")
                    
        except Exception as e:
            print(f"  ❌ Adaptive crawling failed: {e}")
            # Fallback to single page crawl
            article = await crawl_article(site_url)
            if article:
                articles.append(article)
    
    return articles


async def crawl_article(url: str) -> ScrapeArticleResponse | None:
    """Crawl a single article URL and extract content."""
    print(f"  📄 Crawling article: {url}")
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        
        if result.success:
            # Clean the HTML content to focus on article content
            cleaned_html = clean_html(result.html)
            text_content = html_to_text(cleaned_html)
            date = extract_date_from_html(result.html)  # Use original HTML for better metadata extraction
            author = extract_author_from_html(result.html)
            
            article = ScrapeArticleResponse(
                title=result.metadata.get('title', 'No title found'),
                url=result.url,
                text_content=text_content,   # Clean text only
                date=date,
                author=author
            )
            
            print(f"    ✅ Article length: {len(text_content)} chars")
            if date:
                print(f"    📅 Date found: {date}")
            if author:
                print(f"    ✍️  Author found: {author}")
            return article
        else:
            print(f"    ❌ Failed to crawl article: {url}")
            return None


async def main():
    """Main function to crawl multiple news sites using Adaptive Crawling."""
    sites = [
        {"name": "Aftonbladet", "url": "https://aftonbladet.se"},
        {"name": "Polisen", "url": "https://polisen.se/aktuellt/polisens-nyheter/1/?lpfm.loc=Norrt%C3%A4lje"}
    ]
    
    all_results = {}
    
    for site in sites:
        print(f"Processing {site['name']}")
        print(f"{'='*60}")
        
        # Use Adaptive Crawling to find articles
        articles = await adaptive_crawl_news_site(site['url'], site['name'], max_articles=5)
        
        all_results[site['name'].lower()] = {
            "site_url": site['url'],
            "articles_found": len(articles),
            "articles": [article.model_dump() for article in articles]
        }
        
        print(f"✅ Found {len(articles)} articles from {site['name']}")
        print()
    
    # Save results to JSON file
    output_file = "scraped_articles.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"🎉 Results saved to {output_file}")
    print(f"Total articles collected: {sum(data['articles_found'] for data in all_results.values())}")


if __name__ == "__main__":
    asyncio.run(main())