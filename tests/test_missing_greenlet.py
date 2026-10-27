"""Regression tests for sqlalchemy.exc.MissingGreenlet errors.

Root cause: score_news() accessed news.categories (a lazy-loaded ORM
relationship) from synchronous code inside an async session.  Two bugs:

1. process_pending_news() was missing selectinload(News.categories), so the
   relationship was in an unloaded state when score_news() ran.
2. score_news() had two fallback accesses of news.categories that triggered
   a lazy load when category_slugs / primary_category were not supplied.

These tests verify that score_news() never touches news.categories lazily,
and that process_pending_news() queries with both selectinload options.
"""
import asyncio
import pytest
import warnings
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_news(title="Test article", geo="international", published=None):
    from app.models import News, Source
    src = Source(
        id=1, name="Test Source", url="https://test.com/rss",
        reliability_score=0.80, geographic_scope=geo, language="es",
        fetch_interval_minutes=30, consecutive_errors=0,
        total_articles_fetched=0,
    )
    n = News(
        id=1, source_id=1,
        url="https://example.com/1", url_hash="hash1",
        title_original=title, title_es=title,
        summary_original="Resumen de prueba para la noticia de test.",
        language_original="es",
        geographic_scope=geo,
        published_at=published or datetime.now(tz=timezone.utc),
        relevance_score=0.5, relevance_level="follow",
        is_duplicate=False, processing_status="raw",
        translation_status="not_needed",
        categories=[],
    )
    n.source = src
    return n


# ---------------------------------------------------------------------------
# score_news must never access news.categories lazily
# (verified by source inspection — the lazy fallback lines must not exist)
# ---------------------------------------------------------------------------

def test_score_news_source_has_no_lazy_categories_access():
    """score_news() must not contain news.categories accesses that would
    trigger a lazy ORM load from synchronous code in an async session."""
    import inspect
    from app.processing import scoring

    source = inspect.getsource(scoring.score_news)

    # The removed lazy-load fallback lines must not be present
    assert "news.categories[0].slug" not in source, (
        "score_news must not read news.categories[0].slug (lazy load risk)"
    )
    assert "c.slug for c in (news.categories" not in source, (
        "score_news must not iterate news.categories lazily"
    )


def test_score_news_category_slugs_none_treated_as_empty():
    """When category_slugs=None is passed, score_news must treat it as []
    (no categories) rather than falling back to news.categories."""
    from app.processing.scoring import score_news

    news = _make_news("Noticia sin categorías")
    # categories stays as [] (set in _make_news); the fallback path must not
    # try to iterate it via the old 'for c in news.categories' pattern
    score_news(news, category_slugs=None)

    assert news.relevance_score is not None
    assert news.relevance_level in ("featured", "relevant", "follow")


def test_score_news_standard_flow_no_args():
    """score_news() with no explicit args must work and produce a valid score."""
    from app.processing.scoring import score_news

    news = _make_news("Gobierno anuncia medidas de emergencia nacional")
    score_news(news)

    assert news.relevance_score is not None
    assert 0.0 <= news.relevance_score <= 1.0
    assert news.relevance_level in ("featured", "relevant", "follow")


def test_score_news_historia_dispatches_without_lazy_categories():
    """score_news(primary_category='historia') must dispatch to historia scorer
    before any news.categories access."""
    from app.processing.scoring import score_news

    news = _make_news("Descubrimiento arqueológico en Numancia")
    score_news(news, primary_category="historia")
    # historia scorer sets its own score and level
    assert news.relevance_level in ("featured", "relevant", "follow")


def test_score_news_catolicismo_dispatches_without_lazy_categories():
    """score_news(primary_category='catolicismo') must dispatch to catolicismo
    scorer before any news.categories access."""
    from app.processing.scoring import score_news

    news = _make_news("El Papa Francisco visita España")
    score_news(news, primary_category="catolicismo")
    assert news.relevance_level in ("featured", "relevant", "follow")


# ---------------------------------------------------------------------------
# Verify the process_pending_news query loads News.categories eagerly
# ---------------------------------------------------------------------------

def test_process_pending_news_loads_categories_eagerly():
    """process_pending_news() must include selectinload(News.categories)
    so that score_news() never triggers a lazy load on news.categories."""
    import inspect
    from app.ingestion import manager

    source = inspect.getsource(manager.process_pending_news)

    # Both eager-load options must be present in the same query
    assert "selectinload(News.source)" in source, (
        "process_pending_news must eager-load News.source"
    )
    assert "selectinload(News.categories)" in source, (
        "process_pending_news must eager-load News.categories to prevent "
        "MissingGreenlet when score_news() accesses news.categories"
    )


# ---------------------------------------------------------------------------
# Integration: full process_pending_news() run without MissingGreenlet
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_pending_no_missinggreenlet(db_engine):
    """End-to-end: process_pending_news() must complete without raising
    MissingGreenlet or emitting 'Connection.cursor was never awaited' warnings."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from app.models import News, Source, Category
    from app.ingestion.manager import process_pending_news

    TestSession = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        # Seed a source
        src = Source(
            name="Test Source PG", url="https://test.com/rss",
            reliability_score=0.80, geographic_scope="spain", language="es",
            fetch_interval_minutes=30, enabled=True,
            consecutive_errors=0, total_articles_fetched=0,
        )
        session.add(src)
        await session.flush()

        # Seed a category
        cat = Category(slug="politica", name_es="Política", name_en="Politics", icon="🏛️")
        session.add(cat)
        await session.flush()

        # Seed a raw article (no categories yet)
        article = News(
            source_id=src.id,
            url="https://example.com/pg-test",
            url_hash="pg_test_hash_001",
            title_original="El gobierno declara estado de alerta por la crisis",
            title_es="El gobierno declara estado de alerta por la crisis",
            summary_original="El ejecutivo ha activado el protocolo de emergencia.",
            language_original="es",
            geographic_scope="spain",
            published_at=datetime.now(tz=timezone.utc),
            is_duplicate=False,
            processing_status="raw",
            translation_status="not_needed",
            relevance_score=0.5,
            relevance_level="follow",
        )
        session.add(article)
        await session.commit()

    with patch("app.ingestion.manager.AsyncSessionLocal", TestSession):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # Must complete without MissingGreenlet
            await process_pending_news()

    cursor_warnings = [
        w for w in caught
        if "cursor" in str(w.message).lower() and "never awaited" in str(w.message).lower()
    ]
    assert not cursor_warnings, (
        f"'Connection.cursor was never awaited' warnings: {cursor_warnings}"
    )
