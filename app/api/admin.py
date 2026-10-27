from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models import Source, News, SystemLog
from app.schemas import AdminStatsOut, SystemLogOut
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _check_admin(x_admin_token: Optional[str] = Header(None)):
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/stats", response_model=AdminStatsOut)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)

    today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_sources = (await db.execute(select(func.count(Source.id)))).scalar_one()
    active_sources = (await db.execute(
        select(func.count(Source.id)).where(Source.enabled == True)
    )).scalar_one()
    total_news = (await db.execute(select(func.count(News.id)))).scalar_one()
    news_today = (await db.execute(
        select(func.count(News.id)).where(News.ingested_at >= today_start)
    )).scalar_one()
    duplicates = (await db.execute(
        select(func.count(News.id)).where(News.is_duplicate == True)
    )).scalar_one()
    trans_pending = (await db.execute(
        select(func.count(News.id)).where(News.translation_status == "pending")
    )).scalar_one()
    trans_failed = (await db.execute(
        select(func.count(News.id)).where(News.translation_status == "failed")
    )).scalar_one()
    sources_errors = (await db.execute(
        select(func.count(Source.id)).where(Source.consecutive_errors > 0)
    )).scalar_one()

    last_src = (await db.execute(
        select(Source.last_fetched_at).where(Source.last_fetched_at != None)
        .order_by(Source.last_fetched_at.desc()).limit(1)
    )).scalar_one_or_none()

    return AdminStatsOut(
        total_sources=total_sources,
        active_sources=active_sources,
        total_news=total_news,
        news_today=news_today,
        duplicates_detected=duplicates,
        translations_pending=trans_pending,
        translations_failed=trans_failed,
        last_ingestion=last_src,
        sources_with_errors=sources_errors,
    )


@router.get("/logs", response_model=List[SystemLogOut])
async def get_logs(
    level: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)
    stmt = select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)
    if level:
        stmt = stmt.where(SystemLog.level == level)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/run-ingestion")
async def run_ingestion(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)
    from app.ingestion.manager import run_ingestion_cycle
    background_tasks.add_task(run_ingestion_cycle)
    return {"status": "ingestion_started"}


@router.post("/run-processing")
async def run_processing(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)
    from app.scheduler.tasks import processing_task
    background_tasks.add_task(processing_task)
    return {"status": "processing_started"}


@router.post("/reclassify-geo")
async def reclassify_geo(
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    """Recompute geographic_scope for all stored articles using current rules."""
    _check_admin(x_admin_token)
    from app.processing.reclassify import reclassify_geo as _reclassify
    result = await _reclassify(db)
    return result


@router.post("/run-translation")
async def run_translation(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Trigger a translation pass in the background."""
    _check_admin(x_admin_token)

    async def _translate_bg():
        from app.database import AsyncSessionLocal
        from app.translation.translator import translate_pending_news
        async with AsyncSessionLocal() as session:
            await translate_pending_news(session)

    background_tasks.add_task(_translate_bg)
    return {"status": "translation_started"}


@router.post("/reclassify-categories")
async def reclassify_categories_endpoint(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Recompute topic categories for all stored articles using the current algorithm."""
    _check_admin(x_admin_token)

    async def _reclassify_bg():
        from app.database import AsyncSessionLocal
        from app.processing.reclassify import reclassify_categories
        async with AsyncSessionLocal() as session:
            result = await reclassify_categories(session)
            import logging
            logging.getLogger(__name__).info("Category reclassification: %s", result)

    background_tasks.add_task(_reclassify_bg)
    return {"status": "reclassification_started"}


@router.get("/diversity")
async def get_diversity_report(
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    """Editorial diversity audit: article distribution by source, scope, and editorial line."""
    _check_admin(x_admin_token)

    # Articles per source
    rows = (await db.execute(
        select(Source.name, Source.geographic_scope, Source.enabled, Source.extra_config,
               func.count(News.id).label("article_count"))
        .join(News, News.source_id == Source.id, isouter=True)
        .group_by(Source.id)
        .order_by(func.count(News.id).desc())
    )).all()

    total_articles = sum(r.article_count or 0 for r in rows)

    sources_detail = []
    editorial_counts: dict[str, int] = {}
    scope_counts: dict[str, int] = {}

    for r in rows:
        count = r.article_count or 0
        pct = round(count / total_articles * 100, 1) if total_articles else 0
        editorial = (r.extra_config or {}).get("editorial", "desconocida")
        editorial_counts[editorial] = editorial_counts.get(editorial, 0) + count
        scope_counts[r.geographic_scope] = scope_counts.get(r.geographic_scope, 0) + count
        sources_detail.append({
            "name": r.name,
            "scope": r.geographic_scope,
            "enabled": r.enabled,
            "editorial": editorial,
            "articles": count,
            "pct": pct,
        })

    # Concentration index (Herfindahl-Hirschman for editorial lines, normalized 0-1)
    hhi = 0.0
    if total_articles:
        hhi = sum((c / total_articles) ** 2 for c in editorial_counts.values())

    return {
        "total_articles": total_articles,
        "editorial_distribution": {
            k: {"count": v, "pct": round(v / total_articles * 100, 1) if total_articles else 0}
            for k, v in sorted(editorial_counts.items(), key=lambda x: -x[1])
        },
        "scope_distribution": {
            k: {"count": v, "pct": round(v / total_articles * 100, 1) if total_articles else 0}
            for k, v in sorted(scope_counts.items(), key=lambda x: -x[1])
        },
        "concentration_index_hhi": round(hhi, 4),
        "concentration_label": (
            "alta" if hhi > 0.25 else "moderada" if hhi > 0.15 else "baja"
        ),
        "sources": sources_detail,
    }
