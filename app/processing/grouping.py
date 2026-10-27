import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import News, Event
from app.processing.deduplication import _word_overlap_score

logger = logging.getLogger(__name__)


async def group_related_news(session: AsyncSession, window_hours: int = 24):
    """Group news items about the same event."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)

    result = await session.execute(
        select(News)
        .options(selectinload(News.events))
        .where(News.processing_status == "processed")
        .where(News.is_duplicate == False)
        .where(News.published_at >= cutoff)
        .order_by(News.relevance_score.desc())
        .limit(300)
    )
    items = result.scalars().all()

    # Build clusters greedily
    processed_ids = set()

    for lead in items:
        if lead.id in processed_ids:
            continue
        if lead.events:
            processed_ids.add(lead.id)
            continue

        cluster = [lead]
        for other in items:
            if other.id == lead.id or other.id in processed_ids:
                continue
            overlap = _word_overlap_score(lead.title_original, other.title_original)
            if overlap >= 0.55 and other.geographic_scope == lead.geographic_scope:
                cluster.append(other)

        if len(cluster) >= 2:
            # Create or update an event
            event = Event(
                title_es=lead.title_es or lead.title_original,
                summary_es=lead.summary_es or lead.summary_original,
                primary_news_id=lead.id,
                geographic_scope=lead.geographic_scope,
                source_count=len(cluster),
                last_updated_at=datetime.now(tz=timezone.utc),
            )
            session.add(event)
            await session.flush()

            for item in cluster:
                item.events.append(event)
                processed_ids.add(item.id)

    await session.commit()
    logger.info("Grouping completed for window of %dh", window_hours)
