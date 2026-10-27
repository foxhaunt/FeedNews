import logging
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


async def ingestion_task():
    try:
        from app.ingestion.manager import run_ingestion_cycle
        logger.info("Starting scheduled ingestion cycle")
        await run_ingestion_cycle()
        logger.info("Ingestion cycle completed")
    except Exception as e:
        logger.error("Ingestion task failed: %s", e, exc_info=True)


async def processing_task():
    try:
        from app.database import AsyncSessionLocal
        from app.processing.deduplication import run_deduplication
        from app.processing.grouping import group_related_news
        from app.translation.translator import translate_pending_news

        logger.info("Starting processing task")
        async with AsyncSessionLocal() as session:
            await run_deduplication(session)
            await group_related_news(session)
            await translate_pending_news(session)
        logger.info("Processing task completed")
    except Exception as e:
        logger.error("Processing task failed: %s", e, exc_info=True)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
        _scheduler.add_job(
            ingestion_task,
            trigger=IntervalTrigger(minutes=settings.INGESTION_INTERVAL_MINUTES),
            id="ingestion",
            name="RSS Ingestion",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        _scheduler.add_job(
            processing_task,
            trigger=IntervalTrigger(minutes=settings.PROCESSING_INTERVAL_MINUTES),
            id="processing",
            name="News Processing",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    return _scheduler


def start_scheduler():
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info(
            "Scheduler started (ingestion every %dm, processing every %dm)",
            settings.INGESTION_INTERVAL_MINUTES,
            settings.PROCESSING_INTERVAL_MINUTES,
        )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
