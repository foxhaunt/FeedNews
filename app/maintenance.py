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
from app.processing.scoring import score_news

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_CATOLICISMO_SOURCE_NAMES = {
    "InfoVaticana",
    "Adelante la Fe",
    "Periódico La Esperanza",
    "Un Tradi en el Novus Ordo",
    "FSSPX.News (ES)",
    "Vatican News (ES)",
    "Conferencia Episcopal Española",
}

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


async def rescore_historia():
    """Apply the personalized Historia scoring to all processed historia articles.

    Safe to run multiple times. Only affects articles whose primary source
    category is 'historia'. Does not touch other categories or user-saved data.
    """
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(News)
            .options(selectinload(News.source), selectinload(News.categories))
            .join(News.source)
            .where(Source.name.in_(_HISTORIA_SOURCE_NAMES))
            .where(News.processing_status == "processed")
        )
        articles = result.scalars().all()
        logger.info("Found %d processed historia articles to rescore", len(articles))

        rescored = 0
        level_counts: dict = {}

        for news in articles:
            old_level = news.relevance_level
            score_news(news, primary_category="historia")
            level_counts[news.relevance_level] = level_counts.get(news.relevance_level, 0) + 1
            if news.relevance_level != old_level:
                rescored += 1

        await session.commit()
        logger.info(
            "Rescore complete: %d level changes. Distribution: %s",
            rescored, level_counts,
        )
        return rescored, level_counts


async def reclassify_catolicismo():
    """Re-run categorize_news on all articles from catolicismo sources."""
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(News)
            .options(selectinload(News.source), selectinload(News.categories))
            .join(News.source)
            .where(Source.name.in_(_CATOLICISMO_SOURCE_NAMES))
            .where(News.processing_status == "processed")
        )
        articles = result.scalars().all()
        logger.info("Found %d processed articles from catolicismo sources", len(articles))

        reclassified = 0
        geo_fixed = 0

        for news in articles:
            src = news.source
            primary = (src.extra_config or {}).get("primary_category") if src else None
            if not primary:
                primary = "catolicismo"

            old_slugs = sorted(c.slug for c in news.categories)
            new_slugs = await categorize_news(news, session, source_primary_category=primary)

            if sorted(new_slugs) != old_slugs:
                reclassified += 1

            if src and src.geographic_scope == "spain" and news.geographic_scope != "spain":
                news.geographic_scope = "spain"
                geo_fixed += 1

        await session.commit()
        logger.info(
            "Done: %d articles reclassified, %d geographic scopes corrected",
            reclassified, geo_fixed,
        )
        return reclassified, geo_fixed


async def rescore_catolicismo():
    """Apply the personalized Catolicismo scoring to all processed catolicismo articles."""
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(News)
            .options(selectinload(News.source), selectinload(News.categories))
            .join(News.source)
            .where(Source.name.in_(_CATOLICISMO_SOURCE_NAMES))
            .where(News.processing_status == "processed")
        )
        articles = result.scalars().all()
        logger.info("Found %d processed catolicismo articles to rescore", len(articles))

        rescored = 0
        level_counts: dict = {}

        for news in articles:
            old_level = news.relevance_level
            score_news(news, primary_category="catolicismo")
            level_counts[news.relevance_level] = level_counts.get(news.relevance_level, 0) + 1
            if news.relevance_level != old_level:
                rescored += 1

        await session.commit()
        logger.info(
            "Rescore complete: %d level changes. Distribution: %s",
            rescored, level_counts,
        )
        return rescored, level_counts


async def clean_editorial_noise_retroactive(dry_run: bool = False):
    """Remove editorial recommendation blocks from existing summaries in the DB.

    Applies ``clean_editorial_noise`` to ``summary_original`` and
    ``summary_es`` for every article that contains a known marker.  The
    article is NOT re-fetched, re-categorised or re-scored — only the summary
    text fields are updated.

    Pass ``dry_run=True`` to preview changes without writing to the DB.
    """
    from app.ingestion.normalizer import clean_editorial_noise

    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(News))
        all_articles = result.scalars().all()

        updated = 0
        for news in all_articles:
            changed = False

            if news.summary_original:
                cleaned = clean_editorial_noise(news.summary_original)
                if cleaned != news.summary_original:
                    if not dry_run:
                        news.summary_original = cleaned
                    changed = True

            if news.summary_es:
                cleaned_es = clean_editorial_noise(news.summary_es)
                if cleaned_es != news.summary_es:
                    if not dry_run:
                        news.summary_es = cleaned_es
                    changed = True

            if changed:
                updated += 1
                if dry_run:
                    logger.info(
                        "[DRY RUN] Would clean article %d: %s",
                        news.id,
                        (news.title_original or "")[:60],
                    )

        if not dry_run:
            await session.commit()

        mode = "DRY RUN" if dry_run else "updated"
        logger.info("Editorial noise cleanup (%s): %d articles %s", mode, updated, mode)
        return updated


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    if task == "reclassify_historia":
        asyncio.run(reclassify_historia())
    elif task == "rescore_historia":
        asyncio.run(rescore_historia())
    elif task == "reclassify_catolicismo":
        asyncio.run(reclassify_catolicismo())
    elif task == "rescore_catolicismo":
        asyncio.run(rescore_catolicismo())
    elif task == "clean_summaries":
        dry = "--dry-run" in sys.argv
        asyncio.run(clean_editorial_noise_retroactive(dry_run=dry))
    else:
        print("Usage: python -m app.maintenance <command>")
        print("  reclassify_historia    — recategorize + fix geo_scope for historia articles")
        print("  rescore_historia       — apply personalized scoring to historia articles")
        print("  reclassify_catolicismo — recategorize + fix geo_scope for catolicismo articles")
        print("  rescore_catolicismo    — apply personalized scoring to catolicismo articles")
        print("  clean_summaries        — strip editorial noise from existing summaries")
        print("  clean_summaries --dry-run  — preview without writing")
        sys.exit(1)
