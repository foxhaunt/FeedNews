from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Table, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

# Association tables
news_categories = Table(
    "news_categories",
    Base.metadata,
    Column("news_id", Integer, ForeignKey("news.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
)

event_news = Table(
    "event_news",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("events.id"), primary_key=True),
    Column("news_id", Integer, ForeignKey("news.id"), primary_key=True),
)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    feed_type = Column(String(20), default="rss")  # rss, atom, api
    geographic_scope = Column(String(20), default="international")  # spain, europe, international
    language = Column(String(10), default="es")
    reliability_score = Column(Float, default=0.7)
    enabled = Column(Boolean, default=True)
    fetch_interval_minutes = Column(Integer, default=30)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_errors = Column(Integer, default=0)
    total_articles_fetched = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    extra_config = Column(JSON, default=dict)

    news_items = relationship("News", back_populates="source")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, nullable=False)
    name_es = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    icon = Column(String(20), default="📰")
    order = Column(Integer, default=0)

    news_items = relationship("News", secondary=news_categories, back_populates="categories")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    # Identity
    url = Column(String(1000), nullable=False)
    url_hash = Column(String(64), nullable=False, index=True)
    guid = Column(String(500), nullable=True)

    # Content (original)
    title_original = Column(Text, nullable=False)
    summary_original = Column(Text, nullable=True)
    content_original = Column(Text, nullable=True)
    language_original = Column(String(10), default="es")
    image_url = Column(String(1000), nullable=True)

    # Content (Spanish)
    title_es = Column(Text, nullable=True)
    summary_es = Column(Text, nullable=True)
    translation_status = Column(String(20), default="pending")  # pending, done, failed, not_needed
    translation_provider = Column(String(50), nullable=True)

    # Classification
    geographic_scope = Column(String(20), default="international")  # spain, europe, international
    relevance_score = Column(Float, default=0.5)
    relevance_level = Column(String(20), default="follow")  # featured, relevant, follow

    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Deduplication
    duplicate_of_id = Column(Integer, ForeignKey("news.id"), nullable=True)
    is_duplicate = Column(Boolean, default=False)

    # Processing state
    processing_status = Column(String(20), default="raw")  # raw, processed, error

    source = relationship("Source", back_populates="news_items")
    categories = relationship("Category", secondary=news_categories, back_populates="news_items")
    duplicates = relationship("News", foreign_keys=[duplicate_of_id])
    events = relationship("Event", secondary=event_news, back_populates="news_items")

    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_news_url_hash"),
        Index("ix_news_published_at", "published_at"),
        Index("ix_news_relevance", "relevance_score"),
        Index("ix_news_geo_scope", "geographic_scope"),
    )


class Event(Base):
    """Groups of news items about the same real-world event."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title_es = Column(Text, nullable=False)
    summary_es = Column(Text, nullable=True)
    primary_news_id = Column(Integer, ForeignKey("news.id"), nullable=True)
    geographic_scope = Column(String(20), default="international")
    source_count = Column(Integer, default=1)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now())

    news_items = relationship("News", secondary=event_news, back_populates="events")


class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True)
    text_hash = Column(String(64), unique=True, nullable=False, index=True)
    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    provider = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # info, warning, error
    component = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_logs_created_at", "created_at"),
    )
