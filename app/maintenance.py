"""One-off maintenance tasks for FeedNews.

Run with:
    python -m app.maintenance reclassify_historia
"""
import asyncio
import logging
import sys
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, init_db
from app.models import News, Source
from app.processing.categorizer import categorize_news

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_HISTORIA_SOURCE_NAMES = {
    "El Reto Histórico",
    "Muy Interesante Historia",
    "Hispania Sacra (CSIC)",
    "Hispania (CSIC)",
    "En la España Medieval (UCM)",
    "Historia National Geographic",  # disabled but may have articles
}


async def reclassify_historia():
    """Re-run categorize_news on all articles from historia sources.

    Also fixes geographic_scope for those that were incorrectly set to
    'europe' or 'international' when the source declares 'spain'.

    Does NOT delete articles, change URLs, dates, summaries, or translations.
    """
    await init_db()
    async with AsyncSessionLocal() as session:
        # Load all articles from historia sources
        result = await session.execute(
            select(News)
            .options(selectinload(News.source), selectinload(News.categories))
            .join(News.source)
            .where(Source.name.in_(_HISTORIA_SOURCE_NAMES))
            .where(News.processing_status == "processed")
        )
        articles = result.scalars().all()
        logger.info("Found %d processed articles from historia sources", len(articles))

        reclassified = 0
        geo_fixed = 0

        for news in articles:
            src = news.source
            primary = (src.extra_config or {}).get("primary_category") if src else None
            if not primary:
                primary = "historia"

            old_slugs = sorted(c.slug for c in news.categories)

            new_slugs = await categorize_news(news, session, source_primary_category=primary)

            if sorted(new_slugs) != old_slugs:
                reclassified += 1

            # Fix geographic_scope: historia sources declare 'spain'
            if src and src.geographic_scope == "spain" and news.geographic_scope != "spain":
                news.geographic_scope = "spain"
                geo_fixed += 1

        await session.commit()
        logger.info(
            "Done: %d articles reclassified, %d geographic scopes corrected",
            reclassified, geo_fixed,
        )
        return reclassified, geo_fixed


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    if task == "reclassify_historia":
        asyncio.run(reclassify_historia())
    else:
        print("Usage: python -m app.maintenance reclassify_historia")
        sys.exit(1)
