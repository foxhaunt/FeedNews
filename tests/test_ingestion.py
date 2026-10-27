"""Tests for RSS ingestion and normalization."""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone


def make_mock_entry(title, link, summary="Test summary for article", guid=None):
    class Entry:
        pass
    e = Entry()
    e.title = title
    e.link = link
    e.id = guid or link
    e.summary = summary
    e.published_parsed = (2025, 10, 1, 12, 0, 0, 0, 0, 0)
    e.updated_parsed = None
    e.media_thumbnail = []
    e.enclosures = []
    e.links = []
    e.content = []
    return e


def make_mock_feed(entries):
    class Feed:
        bozo = False
        bozo_exception = None
    feed = Feed()
    feed.entries = entries
    return feed


@pytest.mark.asyncio
async def test_fetch_feed_returns_articles():
    from app.ingestion.rss_fetcher import fetch_feed
    from unittest.mock import MagicMock
    from contextlib import asynccontextmanager

    mock_content = b"<rss></rss>"
    entry = make_mock_entry("Test article title here", "https://example.com/article1")
    mock_feed = make_mock_feed([entry])

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=mock_content)
    mock_resp.raise_for_status = MagicMock()

    @asynccontextmanager
    async def fake_get(*a, **kw):
        yield mock_resp

    mock_session = AsyncMock()
    mock_session.get = fake_get

    @asynccontextmanager
    async def fake_session(*a, **kw):
        yield mock_session

    with patch("aiohttp.ClientSession", fake_session), \
         patch("feedparser.parse", return_value=mock_feed):
        articles = await fetch_feed("https://example.com/feed.rss", "en")
        assert len(articles) >= 1
        assert articles[0].title == "Test article title here"
        assert articles[0].url == "https://example.com/article1"


@pytest.mark.asyncio
async def test_fetch_feed_timeout_raises():
    import asyncio
    from app.ingestion.rss_fetcher import fetch_feed
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_get(*a, **kw):
        raise asyncio.TimeoutError()
        yield  # noqa

    mock_session = AsyncMock()
    mock_session.get = fake_get

    @asynccontextmanager
    async def fake_session(*a, **kw):
        yield mock_session

    with patch("aiohttp.ClientSession", fake_session):
        with pytest.raises(RuntimeError, match="Timeout"):
            await fetch_feed("https://example.com/feed.rss")


def test_url_hash_is_deterministic():
    from app.ingestion.rss_fetcher import url_hash
    url = "https://example.com/article?id=123"
    assert url_hash(url) == url_hash(url)
    assert len(url_hash(url)) == 64


def test_normalize_url_strips_tracking():
    from app.ingestion.normalizer import normalize_url
    url = "https://elpais.com/article?utm_source=twitter&utm_medium=social&id=1"
    clean = normalize_url(url)
    assert "utm_source" not in clean
    assert "id=1" in clean


def test_is_valid_article_rejects_short_title():
    from app.ingestion.rss_fetcher import RawArticle
    from app.ingestion.normalizer import is_valid_article
    from datetime import datetime, timezone
    art = RawArticle(
        url="https://example.com", url_hash="abc", guid=None,
        title="short", summary=None, content=None, image_url=None,
        published_at=datetime.now(tz=timezone.utc), updated_at=None, language_hint="es"
    )
    assert not is_valid_article(art)


def test_is_valid_article_accepts_valid():
    from app.ingestion.rss_fetcher import RawArticle
    from app.ingestion.normalizer import is_valid_article
    from datetime import datetime, timezone
    art = RawArticle(
        url="https://example.com/article-1", url_hash="abc123", guid=None,
        title="Este es un titular de noticia válido",
        summary="Resumen breve.", content=None, image_url=None,
        published_at=datetime.now(tz=timezone.utc), updated_at=None, language_hint="es"
    )
    assert is_valid_article(art)


def test_extract_geo_hints_spain():
    from app.ingestion.normalizer import extract_geo_hints
    hints = extract_geo_hints("El gobierno español aprueba el presupuesto", "El ejecutivo de Sánchez")
    assert "spain" in hints


def test_extract_geo_hints_europe():
    from app.ingestion.normalizer import extract_geo_hints
    hints = extract_geo_hints("La Unión Europea debate nuevas sanciones", None)
    assert "europe" in hints


def test_extract_geo_hints_default_international():
    from app.ingestion.normalizer import extract_geo_hints
    hints = extract_geo_hints("Breaking news in Tokyo", None)
    assert "international" in hints


# ---- Seeds ----

def test_seeds_source_count():
    """SOURCES list must have at least 20 entries and include key Spanish sources."""
    from app.seeds import SOURCES
    names = {s["name"] for s in SOURCES}
    assert len(SOURCES) >= 20
    # Fixed broken sources
    assert "La Vanguardia" in names
    assert "POLITICO Europe" in names
    # New diversity sources
    assert "ABC España" in names
    assert "The Objective" in names
    assert "OKDIARIO" in names
    assert "La Gaceta" in names
    assert "La Bandera" in names


def test_seeds_la_vanguardia_url_fixed():
    from app.seeds import SOURCES
    lv = next(s for s in SOURCES if s["name"] == "La Vanguardia")
    assert lv["url"] == "https://www.lavanguardia.com/rss/home.xml"


def test_seeds_politico_url_fixed():
    from app.seeds import SOURCES
    po = next(s for s in SOURCES if s["name"] == "POLITICO Europe")
    assert "politico.eu" in po["url"]


def test_seeds_efe_disabled():
    from app.seeds import SOURCES
    efe = next((s for s in SOURCES if s["name"] == "Agencia EFE"), None)
    if efe:
        assert efe.get("enabled", True) is False


def test_seeds_editorial_diversity():
    """Seeds should represent both left-leaning and right-leaning Spanish sources."""
    from app.seeds import SOURCES
    spain_sources = [s for s in SOURCES if s.get("geographic_scope") == "spain"]
    editorials = {s.get("extra_config", {}).get("editorial", "") for s in spain_sources}
    left_leaning = {"izquierda", "centroizquierda"} & editorials
    right_leaning = {"derecha", "centroderecha"} & editorials
    assert left_leaning, "Should have left-leaning Spanish sources"
    assert right_leaning, "Should have right-leaning Spanish sources"
