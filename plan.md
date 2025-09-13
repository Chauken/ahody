# Ahody General News Scraper - Implementation Plan

## 🎯 Project Overview

**Goal**: Create a general news scraper that can take a domain like "aftonbladet.se" and automatically:
1. Analyze the site structure and layout
2. Discover article URLs using multiple methods
3. Extract articles in bulk
4. Save them to a database for the existing news writer agent

## 🏗️ Architecture Design

### Current State Analysis
- ✅ FastAPI application with single article scraping (`/scrape-article`)
- ✅ Playwright-based browser service with authentication
- ✅ Pydantic AI agent for content processing
- ✅ Article model with metadata support
- ✅ Existing credentials for multiple news sources (NWT, NT, NSD, etc.)

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                     │
├─────────────────────────────────────────────────────────────┤
│ Existing: /scrape-article                                  │
│ New: /discover-news-site, /bulk-scrape, /scraping-jobs     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                            │
├─────────────────────────────────────────────────────────────┤
│ NewsDiscoveryService    │ BulkScraperService               │
│ - Site analysis         │ - Job orchestration              │
│ - Pattern detection     │ - Progress tracking              │
│ - URL discovery         │ - Rate limiting                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Integration Layer                          │
├─────────────────────────────────────────────────────────────┤
│ crawl4ai (Discovery)    │ Existing ScraperService          │
│ - Adaptive crawling     │ - Individual article processing  │
│ - CSS extraction        │ - AI agent integration           │
│ - Pattern recognition   │ - Content cleaning               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                               │
├─────────────────────────────────────────────────────────────┤
│ Enhanced Models:                                            │
│ - NewsSource (site configs, patterns)                      │
│ - ScrapingJob (batch operations)                           │
│ - ArticleLink (URL queue)                                  │
│ - Article (existing, enhanced)                             │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Data Models

### NewsSource
```python
- id: str
- domain: str (e.g., "aftonbladet.se")
- name: str (e.g., "Aftonbladet")
- source_type: NewsSourceType (RSS_FEED | SITEMAP | ARTICLE_LIST | HOMEPAGE_CRAWL)
- base_url: str
- discovery_patterns:
  - rss_feeds: List[str]
  - sitemap_urls: List[str]
  - article_list_selectors: Dict[str, str]
  - article_url_patterns: List[str]
- scraping_config:
  - rate_limit_delay: float
  - max_articles_per_run: int
- metadata: timestamps, active status
```

### ScrapingJob
```python
- id: str
- news_source_id: str
- status: ScrapingJobStatus (PENDING | RUNNING | COMPLETED | FAILED | CANCELLED)
- progress_tracking:
  - total_articles_discovered: int
  - articles_scraped: int
  - articles_failed: int
- configuration:
  - max_articles: int
  - rate_limit_delay: float
- timestamps: created_at, started_at, completed_at
- error_tracking: error_message, failed_urls
```

### ArticleLink
```python
- id: str
- url: str
- news_source_id: str
- discovered_at: str
- scraped_at: Optional[str]
- is_scraped: bool
- title_preview: Optional[str]
```

## 🔍 Discovery Strategy

### Multi-Method Site Analysis
1. **RSS Feed Discovery**
   - Check common paths: `/rss`, `/feed`, `/rss.xml`, `/feed.xml`
   - Parse homepage for RSS link tags
   - Priority: Highest (most reliable)

2. **Sitemap Discovery**
   - Check: `/sitemap.xml`, `/sitemap_index.xml`
   - Parse `robots.txt` for sitemap references
   - Priority: High (structured data)

3. **Article List Analysis**
   - Scan common paths: `/news`, `/articles`, `/latest`
   - Use crawl4ai CSS extraction to identify patterns
   - Priority: Medium (requires pattern matching)

4. **Homepage Crawling**
   - Analyze homepage structure with crawl4ai
   - Extract article link patterns
   - Create regex patterns for future matching
   - Priority: Lowest (fallback method)

## 🚀 Implementation Phases

### Phase 1: Foundation (High Priority)
- [x] Add crawl4ai dependency
- [x] Create enhanced data models
- [x] Implement NewsDiscoveryService
- [ ] Create BulkScraperService
- [ ] Add database persistence layer

### Phase 2: API Integration (Medium Priority)
- [ ] Create discovery API endpoint (`POST /discover-news-site`)
- [ ] Create bulk scraping endpoint (`POST /bulk-scrape`)
- [ ] Add job status endpoint (`GET /scraping-jobs/{id}`)
- [ ] Add articles listing endpoint (`GET /articles`)

### Phase 3: Advanced Features (Low Priority)
- [ ] Add retry mechanisms and error handling
- [ ] Implement job queuing system
- [ ] Add progress notifications
- [ ] Create admin interface for managing sources

### Phase 4: Testing & Optimization (Low Priority)
- [ ] Test with aftonbladet.se
- [ ] Test with other Swedish news sites
- [ ] Performance optimization
- [ ] Rate limiting fine-tuning

## 🔄 Workflow Example

### Discovering a New News Source
```
1. User calls: POST /discover-news-site {"domain": "aftonbladet.se"}
2. NewsDiscoveryService analyzes the site:
   - Tries RSS discovery
   - Tries sitemap discovery
   - Analyzes homepage structure
   - Determines best method
3. Returns NewsSource configuration
4. Optionally saves to database for future use
```

### Bulk Scraping Process
```
1. User calls: POST /bulk-scrape {"news_source_id": "abc123", "max_articles": 50}
2. BulkScraperService:
   - Creates ScrapingJob record
   - Discovers article URLs using NewsSource config
   - Creates ArticleLink records
   - Processes each URL through existing ScraperService
   - Updates job progress
   - Handles errors and retries
3. Returns job ID for status tracking
```

## 🛠️ Technology Integration

### crawl4ai Integration Points
- **Site Discovery**: Use adaptive crawling for pattern recognition
- **CSS Extraction**: Structured data extraction with JsonCssExtractionStrategy
- **Content Analysis**: Leverage crawl4ai's markdown generation
- **Rate Limiting**: Built-in politeness policies

### Existing System Integration
- **ScraperService**: Reuse for individual article processing
- **Pydantic AI Agent**: Keep existing content processing logic
- **Browser Service**: Maintain authentication capabilities
- **Article Model**: Extend with bulk operation metadata

## 📈 Scalability Considerations

### Performance Optimizations
- Concurrent article processing (asyncio)
- Intelligent caching of discovery results
- Rate limiting per news source
- Resumable operations for large batches

### Error Handling
- Graceful degradation when discovery methods fail
- Retry mechanisms with exponential backoff
- Detailed error logging and reporting
- Job cancellation capabilities

## 🔧 Configuration Management

### Environment Variables
```
# Existing
OPENAI_API_KEY=...
WEB_SCRAPING_MODEL=gpt-4o-mini

# New additions needed
DEFAULT_RATE_LIMIT_DELAY=1.0
MAX_CONCURRENT_SCRAPES=5
DISCOVERY_CACHE_TTL=3600
```

### News Source Configurations
- Store discovered patterns in database
- Allow manual override of auto-discovered settings
- Support site-specific authentication (using existing credentials)

## 🎯 Success Metrics

### Functional Goals
- Successfully discover article patterns for major Swedish news sites
- Extract 90%+ of available articles from discovered sources
- Process articles through existing AI pipeline without modification
- Maintain existing single-article scraping functionality

### Performance Goals
- Discovery phase: < 30 seconds per news source
- Bulk scraping: 10-50 articles per minute (respecting rate limits)
- Error rate: < 5% for well-structured news sites
- Resumable operations for jobs > 100 articles

## 🚦 Risk Assessment

### High Risk
- Site structure changes breaking discovery patterns
- Rate limiting causing job failures
- crawl4ai compatibility with existing Playwright setup

### Medium Risk
- Performance impact on existing single-article endpoint
- Database schema changes affecting existing functionality
- Authentication integration with new bulk operations

### Low Risk
- API design changes
- Configuration management complexity
- Error handling edge cases

## 📝 Next Steps

1. **Review and approve this plan**
2. **Set up development environment with crawl4ai**
3. **Implement Phase 1 components**
4. **Test discovery service with aftonbladet.se**
5. **Iterate based on real-world testing results**

---

*This plan provides a comprehensive roadmap for implementing the Ahody general news scraper while maintaining compatibility with existing systems and ensuring scalable, maintainable code.*
