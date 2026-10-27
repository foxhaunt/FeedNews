from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from datetime import datetime


class CategoryOut(BaseModel):
    id: int
    slug: str
    name_es: str
    icon: str

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    id: int
    name: str
    url: str
    geographic_scope: str
    language: str
    reliability_score: float
    enabled: bool
    fetch_interval_minutes: int
    last_fetched_at: Optional[datetime]
    last_error: Optional[str]
    consecutive_errors: int
    total_articles_fetched: int

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    name: str
    url: str
    feed_type: str = "rss"
    geographic_scope: str = "international"
    language: str = "es"
    reliability_score: float = 0.7
    fetch_interval_minutes: int = 30


class NewsOut(BaseModel):
    id: int
    url: str
    title_es: Optional[str]
    title_original: str
    summary_es: Optional[str]
    image_url: Optional[str]
    language_original: str
    translation_status: str
    geographic_scope: str
    relevance_score: float
    relevance_level: str
    published_at: datetime
    updated_at: Optional[datetime]
    ingested_at: datetime
    source: Optional[SourceOut]
    categories: List[CategoryOut] = []
    is_duplicate: bool
    source_count: Optional[int] = 1

    model_config = {"from_attributes": True}


class NewsDetailOut(NewsOut):
    summary_original: Optional[str]
    content_original: Optional[str]
    translation_provider: Optional[str]


class NewsFilter(BaseModel):
    geographic_scope: Optional[str] = None
    category_slug: Optional[str] = None
    relevance_level: Optional[str] = None
    source_id: Optional[int] = None
    language: Optional[str] = None
    q: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: str = "relevance"  # relevance, published_at
    page: int = 1
    page_size: int = 20


class AdminStatsOut(BaseModel):
    total_sources: int
    active_sources: int
    total_news: int
    news_today: int
    duplicates_detected: int
    translations_pending: int
    translations_failed: int
    last_ingestion: Optional[datetime]
    sources_with_errors: int


class SystemLogOut(BaseModel):
    id: int
    level: str
    component: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
