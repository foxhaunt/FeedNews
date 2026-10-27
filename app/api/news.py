from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models import News, Category
from app.schemas import NewsOut, NewsDetailOut

router = APIRouter(prefix="/api/news", tags=["news"])


def _build_filter(
    q: AsyncSession,
    geo: Optional[str],
    category: Optional[str],
    relevance: Optional[str],
    source_id: Optional[int],
    search: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
):
    stmt = (
        select(News)
        .options(
            selectinload(News.source),
            selectinload(News.categories),
        )
        .where(News.is_duplicate == False)
    )

    if geo:
        stmt = stmt.where(News.geographic_scope == geo)
    if relevance:
        stmt = stmt.where(News.relevance_level == relevance)
    if source_id:
        stmt = stmt.where(News.source_id == source_id)
    if date_from:
        stmt = stmt.where(News.published_at >= date_from)
    if date_to:
        stmt = stmt.where(News.published_at <= date_to)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                News.title_es.ilike(pattern),
                News.title_original.ilike(pattern),
                News.summary_es.ilike(pattern),
                News.summary_original.ilike(pattern),
            )
        )
    if category:
        stmt = stmt.join(News.categories).where(Category.slug == category)

    return stmt


@router.get("", response_model=dict)
async def list_news(
    geo: Optional[str] = Query(None, description="spain|europe|international"),
    category: Optional[str] = Query(None),
    relevance: Optional[str] = Query(None, description="featured|relevant|follow"),
    source_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="Search query"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_by: str = Query("relevance", description="relevance|published_at"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = _build_filter(db, geo, category, relevance, source_id, q, date_from, date_to)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Sort
    if sort_by == "published_at":
        stmt = stmt.order_by(desc(News.published_at))
    else:
        stmt = stmt.order_by(desc(News.relevance_score), desc(News.published_at))

    # Paginate
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": [NewsOut.model_validate(n) for n in items],
    }


@router.get("/featured", response_model=List[NewsOut])
async def featured_news(
    geo: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(News)
        .options(selectinload(News.source), selectinload(News.categories))
        .where(News.is_duplicate == False)
        .where(News.relevance_level == "featured")
    )
    if geo:
        stmt = stmt.where(News.geographic_scope == geo)
    if category:
        stmt = stmt.join(News.categories).where(Category.slug == category)
    stmt = stmt.order_by(desc(News.relevance_score), desc(News.published_at)).limit(limit)
    result = await db.execute(stmt)
    return [NewsOut.model_validate(n) for n in result.scalars().all()]


@router.get("/{news_id}", response_model=NewsDetailOut)
async def get_news(news_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(News)
        .options(selectinload(News.source), selectinload(News.categories))
        .where(News.id == news_id)
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return NewsDetailOut.model_validate(news)
