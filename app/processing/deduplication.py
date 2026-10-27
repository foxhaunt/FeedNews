import re
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import News

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    stopwords = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "e",
        "o", "u", "de", "del", "en", "con", "por", "para", "que", "se",
        "the", "a", "an", "of", "in", "on", "at", "to", "for", "is", "are"
    }
    words = [w for w in title.split() if w not in stopwords and len(w) > 2]
    return " ".join(words)


def _word_overlap_score(title_a: str, title_b: str) -> float:
    """Jaccard-like overlap on normalized title words."""
    norm_a = set(_normalize_title(title_a).split())
    norm_b = set(_normalize_title(title_b).split())
    if not norm_a or not norm_b:
        return 0.0
    intersection = norm_a & norm_b
    union = norm_a | norm_b
    return len(intersection) / len(union)


async def find_duplicate(news: News, session: AsyncSession, window_hours: int = 48) -> Optional[News]:
    """Check if a similar news item already exists within the time window."""
    if not news.title_original:
        return None

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
    result = await session.execute(
        select(News)
        .where(
            and_(
                News.id != news.id,
                News.is_duplicate == False,
                News.published_at >= cutoff,
                News.geographic_scope == news.geographic_scope,
            )
        )
        .order_by(News.relevance_score.desc())
        .limit(100)
    )
    candidates = result.scalars().all()

    best_score = 0.0
    best_candidate: Optional[News] = None
    for candidate in candidates:
        overlap = _word_overlap_score(news.title_original, candidate.title_original)
        if overlap > best_score:
            best_score = overlap
            best_candidate = candidate

    # Mark as duplicate if overlap >= 0.6
    if best_score >= 0.6:
        return best_candidate
    return None


async def run_deduplication(session: AsyncSession, limit: int = 500):
    """Find and mark duplicates among recently ingested unprocessed news."""
    result = await session.execute(
        select(News)
        .where(News.processing_status == "raw")
        .where(News.is_duplicate == False)
        .order_by(News.published_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()

    marked = 0
    for news in items:
        duplicate_of = await find_duplicate(news, session)
        if duplicate_of:
            news.is_duplicate = True
            news.duplicate_of_id = duplicate_of.id
            marked += 1

    await session.commit()
    logger.info("Deduplication: marked %d duplicates out of %d items", marked, len(items))
    return marked
