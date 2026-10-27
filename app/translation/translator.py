import hashlib
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import News, TranslationCache
from app.config import settings

logger = logging.getLogger(__name__)


def _text_hash(text: str, source: str, target: str) -> str:
    key = f"{source}:{target}:{text}"
    return hashlib.sha256(key.encode()).hexdigest()


def _get_provider():
    provider_name = (settings.TRANSLATION_PROVIDER or "").lower()
    if provider_name == "openai":
        from app.translation.providers.openai_provider import OpenAITranslator
        p = OpenAITranslator()
        if p.available:
            return p
    elif provider_name == "anthropic":
        from app.translation.providers.anthropic_provider import AnthropicTranslator
        p = AnthropicTranslator()
        if p.available:
            return p
    elif provider_name == "libre":
        from app.translation.providers.libre import LibreTranslator
        return LibreTranslator()
    elif provider_name in ("gtx", "google_free", ""):
        from app.translation.providers.gtx import GtxTranslator
        return GtxTranslator()
    elif provider_name == "mymemory":
        from app.translation.providers.mymemory import MyMemoryTranslator
        p = MyMemoryTranslator()
        if p.available:
            return p
    elif provider_name == "none":
        return None
    return None


async def translate_text(text: str, source_lang: str, session: AsyncSession) -> tuple[Optional[str], Optional[str]]:
    """Returns (translated_text, provider_name) or (None, None)."""
    if not text or source_lang == "es":
        return text, None

    h = _text_hash(text, source_lang, "es")

    # Check cache
    cached = await session.execute(
        select(TranslationCache).where(TranslationCache.text_hash == h)
    )
    entry = cached.scalar_one_or_none()
    if entry:
        return entry.translated_text, entry.provider

    provider = _get_provider()
    if not provider:
        return None, None

    try:
        result = await provider.translate(text, source_lang, "es")
        if result:
            cache_entry = TranslationCache(
                text_hash=h,
                source_lang=source_lang,
                target_lang="es",
                original_text=text[:4000],
                translated_text=result[:4000],
                provider=provider.name,
            )
            session.add(cache_entry)
            return result, provider.name
    except Exception as e:
        logger.error("Translation error: %s", e)

    return None, None


async def translate_pending_news(session: AsyncSession, limit: int = 30):
    """Translate news items that need translation.

    Processes both 'pending' articles and 'failed' ones that haven't had
    too many attempts.  Adds a small delay between requests to respect
    MyMemory's rate limit (anonymous: 10 000 words/day).
    """
    import asyncio

    provider = _get_provider()
    if not provider:
        logger.debug("No translation provider configured — skipping")
        return 0

    # Fetch pending + retryable-failed items
    result = await session.execute(
        select(News)
        .where(
            News.translation_status.in_(["pending", "failed"])
        )
        .where(News.is_duplicate == False)
        # Avoid retrying articles already showing their original as fallback
        # (those have title_es = title_original; real untranslated ones have title_es = None)
        .where(
            (News.title_es == None) |
            (News.translation_status == "pending")
        )
        .limit(limit)
    )
    items = result.scalars().all()

    translated = 0
    no_provider_count = 0

    for news in items:
        try:
            title_es, prov_name = await translate_text(
                news.title_original, news.language_original, session
            )
            # Pause between every API call to stay under MyMemory's 5 req/s limit
            await asyncio.sleep(0.25)
            if title_es:
                news.title_es = title_es
                # Translate summary (best-effort; doesn't affect status)
                if news.summary_original:
                    summary_es, _ = await translate_text(
                        news.summary_original, news.language_original, session
                    )
                    await asyncio.sleep(0.25)
                    if summary_es:
                        news.summary_es = summary_es
                news.translation_status = "done"
                news.translation_provider = prov_name
                translated += 1
            else:
                # Provider returned nothing — either no provider or rate-limited.
                # Do NOT overwrite title_es with the original; keep status "pending"
                # so it will be retried in the next cycle.
                no_provider_count += 1

        except Exception as e:
            # Hard failure — keep title_es as-is, mark failed so we don't loop forever
            news.translation_status = "failed"
            if not news.title_es:
                news.title_es = news.title_original  # fallback display only
            logger.error("Failed to translate news %d: %s", news.id, e)

    # Backfill: Spanish articles that don't have title_es yet
    result2 = await session.execute(
        select(News)
        .where(News.translation_status == "not_needed")
        .where(News.title_es == None)
        .limit(500)
    )
    for news in result2.scalars().all():
        news.title_es = news.title_original
        news.summary_es = news.summary_original

    await session.commit()
    if no_provider_count:
        logger.warning(
            "Translation: %d items translated, %d skipped (provider unavailable/rate-limited)",
            translated, no_provider_count,
        )
    else:
        logger.info("Translated %d news items", translated)
    return translated
