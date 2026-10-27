import feedparser
import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


def _parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                import time
                ts = time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
    return datetime.now(tz=timezone.utc)


def _extract_image(entry) -> Optional[str]:
    # Try media:thumbnail or enclosure
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "enclosures"):
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href") or enc.get("url")
    if hasattr(entry, "links"):
        for link in entry.links:
            if link.get("type", "").startswith("image/"):
                return link.get("href")
    # Try to extract from summary html
    summary = getattr(entry, "summary", "") or ""
    if "<img" in summary:
        try:
            soup = BeautifulSoup(summary, "lxml")
            img = soup.find("img")
            if img and img.get("src"):
                return img["src"]
        except Exception:
            pass
    return None


def _clean_html(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    try:
        soup = BeautifulSoup(text, "lxml")
        return soup.get_text(separator=" ").strip()[:2000]
    except Exception:
        return text[:2000]


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class RawArticle:
    __slots__ = [
        "url", "url_hash", "guid", "title", "summary", "content",
        "image_url", "published_at", "updated_at", "language_hint"
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


async def fetch_feed(
    feed_url: str,
    source_language: str = "es",
    ssl_verify: bool = True,
) -> List[RawArticle]:
    """Fetch and parse an RSS/Atom feed, returning raw article objects."""
    timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT_SECONDS)
    headers = {
        "User-Agent": "FeedNews/1.0 (+https://github.com/feedNews) RSS Reader",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    ssl_context = False if not ssl_verify else None  # False = skip verification

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(
                feed_url, allow_redirects=True, max_redirects=5, ssl=ssl_context
            ) as resp:
                resp.raise_for_status()
                content = await resp.read()
    except asyncio.TimeoutError:
        raise RuntimeError(f"Timeout fetching {feed_url}")
    except Exception as e:
        raise RuntimeError(f"HTTP error fetching {feed_url}: {e}")

    try:
        feed = feedparser.parse(content)
    except Exception as e:
        raise RuntimeError(f"Parse error for {feed_url}: {e}")

    if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
        exc = getattr(feed, "bozo_exception", None)
        raise RuntimeError(f"Malformed feed {feed_url}: {exc}")

    articles = []
    for entry in feed.entries[: settings.MAX_ARTICLES_PER_SOURCE]:
        link = getattr(entry, "link", None) or getattr(entry, "id", None)
        if not link:
            continue

        title = getattr(entry, "title", "").strip()
        if not title:
            continue

        summary_raw = getattr(entry, "summary", None) or getattr(entry, "description", None)
        content_raw = None
        if hasattr(entry, "content") and entry.content:
            content_raw = entry.content[0].get("value") if isinstance(entry.content, list) else None

        summary = _clean_html(summary_raw)
        content = _clean_html(content_raw) if content_raw else None

        art = RawArticle(
            url=link.strip(),
            url_hash=url_hash(link.strip()),
            guid=getattr(entry, "id", None),
            title=title,
            summary=summary,
            content=content,
            image_url=_extract_image(entry),
            published_at=_parse_date(entry),
            updated_at=None,
            language_hint=source_language,
        )
        articles.append(art)

    logger.info("Fetched %d articles from %s", len(articles), feed_url)
    return articles
