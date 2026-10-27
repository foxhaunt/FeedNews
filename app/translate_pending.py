"""
Manual translation runner.

Usage:
    python -m app.translate_pending              # process 100 pending articles
    python -m app.translate_pending --limit 500  # custom limit
    python -m app.translate_pending --all        # process everything in batches
"""
import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _run(limit: int, all_pending: bool) -> int:
    from app.database import init_db, AsyncSessionLocal
    from app.translation.translator import translate_pending_news
    from sqlalchemy import text

    await init_db()
    total = 0

    async with AsyncSessionLocal() as session:
        if all_pending:
            # Count how many are pending
            result = await session.execute(
                text("SELECT COUNT(*) FROM news WHERE translation_status='pending' AND is_duplicate=0")
            )
            count = result.scalar() or 0
            logger.info("Processing all %d pending articles in batches of 50", count)
            batch_size = 50
            while True:
                translated = await translate_pending_news(session, limit=batch_size)
                total += translated
                if translated == 0:
                    break
                logger.info("Batch done: %d translated this pass, %d total so far", translated, total)
        else:
            logger.info("Processing up to %d pending articles", limit)
            total = await translate_pending_news(session, limit=limit)

    logger.info("Done. Total translated: %d", total)
    return total


def main():
    parser = argparse.ArgumentParser(description="Translate pending news articles")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max articles to translate (default: 100)")
    parser.add_argument("--all", action="store_true",
                        help="Process ALL pending articles in batches")
    args = parser.parse_args()

    translated = asyncio.run(_run(limit=args.limit, all_pending=args.all))
    sys.exit(0 if translated >= 0 else 1)


if __name__ == "__main__":
    main()
