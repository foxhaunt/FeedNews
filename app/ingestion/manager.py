import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Source, News, SystemLog
from app.ingestion.rss_fetcher import fetch_feed, url_hash
from app.ingestion.normalizer import is_valid_article, normalize_url
from app.processing.categorizer import categorize_news
from app.processing.scoring import score_news

logger = logging.getLogger(__name__)


async def _log(session: AsyncSession, level: str, component: str, message: str, details=None):
    entry = SystemLog(level=level, component=component, message=message, details=details)
    session.add(entry)


async def _fetch_source(source: Source) -> tuple:
    """Returns (articles, error_message)."""
    try:
        articles = await fetch_feed(source.url, source.language)
        return articles, None
    except Exception as e:
        return [], str(e)


async def ingest_source(source_id: int):
    """Fetch and store all new articles from one source."""
    async with AsyncSessionLocal() as session:
        source = await session.get(Source, source_id)
        if not source or not source.enabled:
            return

        articles, error = await _fetch_source(source)
        now = datetime.now(tz=timezone.utc)

        if error:
            source.last_error = error
            source.last_error_at = now
            source.consecutive_errors = (source.consecutive_errors or 0) + 1
            await _log(session, "error", "ingestion",
                       f"Error fetching {source.name}: {error}",
                       {"source_id": source_id})
            await session.commit()
            return

        source.last_fetched_at = now
        source.last_error = None
        source.consecutive_errors = 0

        new_count = 0
        for raw in articles:
            if not is_valid_article(raw):
                continue

            clean_url = normalize_url(raw.url)
            h = url_hash(clean_url)

            # Check for existing
            existing = await session.execute(
                select(News).where(News.url_hash == h)
            )
            if existing.scalar_one_or_none():
                continue

            # Detect language
            lang = raw.language_hint
            try:
                from app.translation.detector import detect_language
                if raw.summary:
                    detected = detect_language(raw.title + " " + raw.summary)
                else:
                    detected = detect_language(raw.title)
                if detected:
                    lang = detected
            except Exception:
                pass

            geo_scope = source.geographic_scope
            try:
                from app.ingestion.normalizer import extract_geo_hints
                hints = extract_geo_hints(raw.title, raw.summary)
                if hints:
                    geo_scope = hints[0]
            except Exception:
                pass

            news = News(
                source_id=source.id,
                url=clean_url,
                url_hash=h,
                guid=raw.guid,
                title_original=raw.title,
                summary_original=raw.summary,
                content_original=raw.content,
                language_original=lang,
                image_url=raw.image_url,
                geographic_scope=geo_scope,
                published_at=raw.published_at,
                updated_at=raw.updated_at,
                # Set Spanish title immediately so article is visible without translation step
                title_es=raw.title if lang == "es" else None,
                summary_es=raw.summary if lang == "es" else None,
                translation_status="pending" if lang != "es" else "not_needed",
                processing_status="raw",
            )
            session.add(news)
            new_count += 1

        source.total_articles_fetched = (source.total_articles_fetched or 0) + new_count
        await session.commit()
        logger.info("Source %s: ingested %d new articles", source.name, new_count)


async def process_pending_news():
    """Categorize and score recently ingested news."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(News)
            .options(selectinload(News.source))
            .where(News.processing_status == "raw")
            .where(News.is_duplicate == False)
            .limit(200)
        )
        news_items = result.scalars().all()

        for news in news_items:
            try:
                cat_slugs = await categorize_news(news, session)
                score_news(news, category_slugs=cat_slugs)
                news.processing_status = "processed"
                from datetime import datetime, timezone
                news.processed_at = datetime.now(tz=timezone.utc)
            except Exception as e:
                news.processing_status = "error"
                logger.error("Error processing news %d: %s", news.id, e)

        await session.commit()
        logger.info("Processed %d news items", len(news_items))


async def run_ingestion_cycle():
    """Main ingestion cycle: fetch all due sources, then process."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Source).where(Source.enabled == True)
        )
        sources = result.scalars().all()

    def _as_utc(dt):
        """Ensure a datetime is UTC-aware (SQLite returns naive datetimes)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    now = datetime.now(tz=timezone.utc)
    due_sources = []
    for s in sources:
        if s.consecutive_errors and s.consecutive_errors >= 5:
            last_err = _as_utc(s.last_error_at)
            if last_err and (now - last_err) < timedelta(hours=1):
                continue
        last_fetched = _as_utc(s.last_fetched_at)
        if last_fetched is None:
            due_sources.append(s)
        else:
            due_mins = (now - last_fetched).total_seconds() / 60
            if due_mins >= s.fetch_interval_minutes:
                due_sources.append(s)

    logger.info("Running ingestion for %d sources", len(due_sources))

    # Run fetches concurrently with a limit
    from app.config import settings
    sem = asyncio.Semaphore(settings.MAX_CONCURRENT_FETCHES)

    async def _bounded(source_id):
        async with sem:
            await ingest_source(source_id)

    await asyncio.gather(*[_bounded(s.id) for s in due_sources], return_exceptions=True)
    await process_pending_news()
