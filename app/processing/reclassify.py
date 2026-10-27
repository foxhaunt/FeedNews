"""Reclassify geographic scope and topic categories for existing news items.

Both functions are idempotent: safe to run multiple times; only articles
whose classification would change are updated.
"""
import logging
from sqlalchemy import select, update, insert, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.normalizer import extract_geo_hints
from app.models import News, Category, news_categories
from app.processing.categorizer import classify_text

logger = logging.getLogger(__name__)


async def reclassify_geo(session: AsyncSession, limit: int = 2000) -> dict:
    """Recompute geographic_scope for stored articles using current rules.

    Returns a dict with counts: {"checked": N, "changed": M, "by_scope": {...}}
    """
    result = await session.execute(
        select(News.id, News.title_original, News.summary_original,
               News.geographic_scope, News.source_id)
        .limit(limit)
    )
    rows = result.all()

    changed = 0
    by_scope: dict[str, int] = {}
    updates = []

    for row in rows:
        hints = extract_geo_hints(row.title_original, row.summary_original)
        new_scope = hints[0] if hints else "international"

        if new_scope != row.geographic_scope:
            updates.append({"id": row.id, "geographic_scope": new_scope})
            by_scope[new_scope] = by_scope.get(new_scope, 0) + 1
            changed += 1

    if updates:
        # Bulk update in batches
        for upd in updates:
            await session.execute(
                update(News)
                .where(News.id == upd["id"])
                .values(geographic_scope=upd["geographic_scope"])
            )
        await session.commit()

    logger.info("Reclassification: %d checked, %d changed — %s", len(rows), changed, by_scope)
    return {"checked": len(rows), "changed": changed, "by_scope": by_scope}


async def reclassify_categories(session: AsyncSession, limit: int = 5000) -> dict:
    """Recompute topic categories for stored articles using the current algorithm.

    Only articles whose category set actually changes are updated.
    Returns stats: {"checked": N, "changed": M, "total_assignments": K}
    """
    # Fetch all articles with their current categories
    result = await session.execute(
        select(News.id, News.title_original, News.summary_original)
        .where(News.is_duplicate == False)
        .limit(limit)
    )
    rows = result.all()

    # Load the full category slug→id mapping once
    cat_result = await session.execute(select(Category))
    slug_to_id = {c.slug: c.id for c in cat_result.scalars().all()}

    # Load current category assignments for all articles in one query
    nc_result = await session.execute(
        select(news_categories.c.news_id, Category.slug)
        .join(Category, news_categories.c.category_id == Category.id)
        .where(news_categories.c.news_id.in_([r.id for r in rows]))
    )
    current_cats: dict[int, set] = {}
    for news_id, slug in nc_result.all():
        current_cats.setdefault(news_id, set()).add(slug)

    changed = 0
    total_assignments = 0

    for row in rows:
        new_slugs = classify_text(row.title_original, row.summary_original)
        new_set = set(new_slugs)
        old_set = current_cats.get(row.id, set())

        if new_set == old_set:
            total_assignments += len(new_set)
            continue

        # Update: delete old, insert new
        await session.execute(
            delete(news_categories).where(news_categories.c.news_id == row.id)
        )
        valid_slugs = [s for s in new_slugs if s in slug_to_id]
        if valid_slugs:
            await session.execute(
                insert(news_categories),
                [{"news_id": row.id, "category_id": slug_to_id[slug]}
                 for slug in valid_slugs],
            )
        total_assignments += len(valid_slugs)
        changed += 1

    await session.commit()

    logger.info(
        "Category reclassification: %d checked, %d changed, %d total assignments",
        len(rows), changed, total_assignments,
    )
    return {
        "checked": len(rows),
        "changed": changed,
        "total_assignments": total_assignments,
    }
