# For simplicity, this file contains all the models for the app.
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator


class ArticleMetadata(BaseModel):
    page_title: str = Field(..., description="The title of the page")
    fetch_time: str = Field(..., description="ISO-formatted timestamp when the article was fetched")
    word_count: int = Field(0, description="Number of words in the article content")

    @field_validator("fetch_time")
    def validate_fetch_time(cls, v):
        """Ensure fetch_time is a valid ISO format string."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            return datetime.now().isoformat()


class Article(BaseModel):
    title: str = Field(..., description="The title of the article")
    url: str = Field(..., description="The URL of the article")
    html_content: str = Field(..., description="The raw HTML content of the article")
    text_content: str = Field(..., description="The plain text content of the article")
    date: str | None = Field(None, description="The publication date of the article")
    author: str | None = Field(None, description="The author of the article")

    metadata: ArticleMetadata = Field(..., description="Metadata about the article")

    @field_validator("date")
    def validate_date(cls, v):
        """Allow date to be None or ensure it's a valid format."""
        if v is None:
            return v
        # Simple validation - can be expanded based on expected formats
        if len(v) < 3:
            return None
        return v

    def word_count(self) -> int:
        """Get the word count from the article."""
        return self.metadata.word_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()
