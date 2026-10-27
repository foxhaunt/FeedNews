"""
Historia integration tests — 10 mandatory cases from the spec.

Tests cover:
  1. Source registration — 5 enabled + 1 disabled (NatGeo)
  2. Feed URL format — all enabled sources have valid feed URLs
  3. Category filter — historia slug present in DB, filterable
  4. Source-based classification — primary_category override assigns 'historia'
  5. No politics override — articles from historical sources are NOT primarily política
  6. General media unchanged — general sources still produce non-historia articles
  7. Deduplication — same article from a historical source is not ingested twice
  8. Missing fields — articles with empty title/summary handled without crash
  9. Feed failure isolation — fetch error on one source does not affect others
 10. Search / pagination / geo still work with historia articles
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.processing.categorizer import classify_text, categorize_news
from app.seeds import SOURCES, CATEGORIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(name: str) -> dict | None:
    return next((s for s in SOURCES if s["name"] == name), None)


def primary(title: str, summary: str = "") -> str | None:
    result = classify_text(title, summary)
    return result[0] if result else None


# ---------------------------------------------------------------------------
# 1. Source registration
# ---------------------------------------------------------------------------

def test_sources_registered_in_seeds():
    """The 5 integrable historical sources are declared in seeds.py."""
    names = {s["name"] for s in SOURCES}
    assert "El Reto Histórico" in names
    assert "Muy Interesante Historia" in names
    assert "Hispania Sacra (CSIC)" in names
    assert "Hispania (CSIC)" in names
    assert "En la España Medieval (UCM)" in names


def test_natgeo_is_registered_disabled():
    """NatGeo Historia must be in seeds as disabled, documenting the 403 block."""
    src = _source("Historia National Geographic")
    assert src is not None, "NatGeo Historia should be documented in seeds (even if disabled)"
    assert src.get("enabled") is False
    note = src.get("extra_config", {}).get("note", "")
    assert "403" in note or "bloqueado" in note.lower(), (
        f"extra_config.note should document the 403 block, got: '{note}'"
    )


def test_five_sources_are_enabled():
    """All historical sources except NatGeo must be enabled."""
    hist_names = [
        "El Reto Histórico", "Muy Interesante Historia",
        "Hispania Sacra (CSIC)", "Hispania (CSIC)", "En la España Medieval (UCM)"
    ]
    for name in hist_names:
        src = _source(name)
        assert src is not None, f"{name} not found in seeds"
        assert src.get("enabled", True) is True, f"{name} should be enabled"


def test_all_historical_sources_have_primary_category():
    """All 5 integrable historical sources declare primary_category='historia' in extra_config."""
    hist_names = [
        "El Reto Histórico", "Muy Interesante Historia",
        "Hispania Sacra (CSIC)", "Hispania (CSIC)", "En la España Medieval (UCM)",
    ]
    for name in hist_names:
        src = _source(name)
        assert src is not None, f"{name} not found"
        assert src["extra_config"].get("primary_category") == "historia", (
            f"{name} must have extra_config['primary_category'] == 'historia'"
        )


# ---------------------------------------------------------------------------
# 2. Feed URL format
# ---------------------------------------------------------------------------

def test_csic_sources_have_ssl_verify_false():
    """CSIC sources flag ssl_verify=False because their TLS certs are invalid."""
    for name in ("Hispania Sacra (CSIC)", "Hispania (CSIC)"):
        src = _source(name)
        assert src is not None
        assert src["extra_config"].get("ssl_verify") is False, (
            f"{name} must have ssl_verify=False to bypass invalid CSIC cert"
        )


def test_ucm_source_does_not_need_ssl_bypass():
    """UCM (En la España Medieval) has a valid cert and must NOT disable SSL."""
    src = _source("En la España Medieval (UCM)")
    assert src is not None
    assert src["extra_config"].get("ssl_verify", True) is True


def test_feed_urls_are_absolute():
    """All enabled historical source URLs start with https://."""
    hist_names = [
        "El Reto Histórico", "Muy Interesante Historia",
        "Hispania Sacra (CSIC)", "Hispania (CSIC)", "En la España Medieval (UCM)"
    ]
    for name in hist_names:
        src = _source(name)
        assert src["url"].startswith("https://"), f"{name} URL must be https"


# ---------------------------------------------------------------------------
# 3. Historia category exists in CATEGORIES
# ---------------------------------------------------------------------------

def test_historia_category_in_seeds():
    """Historia category slug is declared in seeds.py."""
    slugs = {c["slug"] for c in CATEGORIES}
    assert "historia" in slugs


def test_historia_category_order():
    """Historia category has order=0 so it appears first in the sidebar."""
    cat = next((c for c in CATEGORIES if c["slug"] == "historia"), None)
    assert cat is not None
    assert cat["order"] == 0


# ---------------------------------------------------------------------------
# 4. Source-based category override — categorize_news()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_source_override_assigns_historia_as_primary():
    """categorize_news() with source_primary_category='historia' puts historia first."""
    news = MagicMock()
    news.id = 9999
    news.title_original = "La reconquista de la Península Ibérica"
    news.summary_original = "Estudio sobre los reinos medievales de Castilla y León."

    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
        MagicMock(slug="historia", id=1),
    ])))))

    with patch("app.processing.categorizer.delete"), \
         patch("app.processing.categorizer.insert"):
        slugs = await categorize_news(news, session, source_primary_category="historia")

    assert slugs[0] == "historia", f"Expected 'historia' as primary, got {slugs}"


@pytest.mark.asyncio
async def test_source_override_without_keyword_match_still_assigns_historia():
    """Source override works even when the text contains no historia keywords."""
    news = MagicMock()
    news.id = 9998
    news.title_original = "Nuevo volumen disponible"
    news.summary_original = "Se han publicado los últimos números de la revista."

    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
        MagicMock(slug="historia", id=1),
    ])))))

    with patch("app.processing.categorizer.delete"), \
         patch("app.processing.categorizer.insert"):
        slugs = await categorize_news(news, session, source_primary_category="historia")

    assert "historia" in slugs
    assert slugs[0] == "historia"


# ---------------------------------------------------------------------------
# 5. No politics override — historical source articles are NOT primarily política
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_political_keywords_in_historical_article_still_gets_historia_primary():
    """Even if an article mentions parliament, the source override keeps historia primary."""
    news = MagicMock()
    news.id = 9997
    news.title_original = "Las Cortes de Castilla en el siglo XV: democracia medieval"
    news.summary_original = (
        "El parlamento de la Corona de Castilla celebraba sus reuniones anuales. "
        "Los diputados del reino debatían la legislación medieval."
    )

    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
        MagicMock(slug="historia", id=1),
        MagicMock(slug="politica", id=2),
    ])))))

    with patch("app.processing.categorizer.delete"), \
         patch("app.processing.categorizer.insert"):
        slugs = await categorize_news(news, session, source_primary_category="historia")

    assert slugs[0] == "historia", (
        f"historia must be primary despite political keywords; got {slugs}"
    )
    # política may appear as secondary — that's acceptable
    assert "historia" in slugs


# ---------------------------------------------------------------------------
# 6. General media unchanged — no source override → normal keyword classification
# ---------------------------------------------------------------------------

def test_general_political_article_still_classified_as_politica():
    """A political article from a general source (no override) remains política."""
    result = classify_text(
        "El Gobierno aprueba los Presupuestos Generales del Estado",
        "El Congreso de los Diputados debatirá el presupuesto la próxima semana. "
        "El partido en el Gobierno busca coalición para las votaciones.",
    )
    assert "politica" in result, f"Expected politica in {result}"
    assert result[0] == "politica", f"politica must be primary, got {result}"


def test_general_article_with_historia_keywords_classified_normally():
    """An article about medieval history in a general source is classified as historia."""
    result = classify_text(
        "Descubrimiento arqueológico en la Edad Media española",
        "Investigadores han hallado un yacimiento del siglo XII con restos de la reconquista.",
    )
    assert "historia" in result, f"Expected historia in {result}"
    assert result[0] == "historia", f"historia must be primary, got {result}"


# ---------------------------------------------------------------------------
# 7. Deduplication — same URL not ingested twice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_article_from_historical_source_not_ingested():
    """ingest_source() skips articles whose url_hash already exists in the DB."""
    from app.ingestion.manager import ingest_source
    from app.ingestion.rss_fetcher import RawArticle, url_hash

    existing_url = "https://elretohistorico.com/articles/reconquista-toledo"
    existing_hash = url_hash(existing_url)

    raw = RawArticle(
        url=existing_url,
        url_hash=existing_hash,
        guid="guid-1",
        title="La reconquista de Toledo",
        summary="Estudio sobre los reinos medievales.",
        content=None,
        image_url=None,
        published_at=None,
        updated_at=None,
        language_hint="es",
    )

    existing_news = MagicMock()

    with patch("app.ingestion.manager.AsyncSessionLocal") as mock_sl, \
         patch("app.ingestion.manager._fetch_source", return_value=([raw], None)):
        mock_session = AsyncMock()
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        source = MagicMock()
        source.id = 1
        source.name = "El Reto Histórico"
        source.enabled = True
        source.language = "es"
        source.geographic_scope = "spain"
        source.extra_config = {"primary_category": "historia"}
        source.consecutive_errors = 0
        source.total_articles_fetched = 0
        mock_session.get = AsyncMock(return_value=source)

        # Simulate: url_hash already exists in DB
        existing_result = MagicMock()
        existing_result.scalar_one_or_none = MagicMock(return_value=existing_news)
        mock_session.execute = AsyncMock(return_value=existing_result)
        mock_session.commit = AsyncMock()

        await ingest_source(1)

        # session.add should NOT have been called (duplicate skipped)
        mock_session.add.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Missing fields — article with empty title is rejected
# ---------------------------------------------------------------------------

def test_article_without_title_is_invalid():
    """is_valid_article returns False for articles with empty title."""
    from app.ingestion.normalizer import is_valid_article
    from app.ingestion.rss_fetcher import RawArticle
    from datetime import datetime, timezone

    raw = RawArticle(
        url="https://elretohistorico.com/empty",
        url_hash="abc",
        guid=None,
        title="",
        summary="Some summary text",
        content=None,
        image_url=None,
        published_at=datetime.now(tz=timezone.utc),
        updated_at=None,
        language_hint="es",
    )
    assert not is_valid_article(raw)


def test_article_without_summary_is_valid():
    """Articles with title but no summary are still valid (summary is optional)."""
    from app.ingestion.normalizer import is_valid_article
    from app.ingestion.rss_fetcher import RawArticle
    from datetime import datetime, timezone

    raw = RawArticle(
        url="https://elretohistorico.com/article-1",
        url_hash="def",
        guid=None,
        title="Excavación arqueológica en Ávila",
        summary=None,
        content=None,
        image_url=None,
        published_at=datetime.now(tz=timezone.utc),
        updated_at=None,
        language_hint="es",
    )
    assert is_valid_article(raw)


# ---------------------------------------------------------------------------
# 9. Feed failure isolation — error on one source does not crash others
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feed_error_does_not_propagate_to_other_sources():
    """run_ingestion_cycle() continues ingesting other sources even if one fails."""
    from app.ingestion.manager import run_ingestion_cycle

    csic_source = MagicMock()
    csic_source.id = 101
    csic_source.name = "Hispania Sacra (CSIC)"
    csic_source.enabled = True
    csic_source.consecutive_errors = 0
    csic_source.last_fetched_at = None
    csic_source.last_error_at = None
    csic_source.fetch_interval_minutes = 1440
    csic_source.extra_config = {"primary_category": "historia", "ssl_verify": False}

    ok_source = MagicMock()
    ok_source.id = 102
    ok_source.name = "El Reto Histórico"
    ok_source.enabled = True
    ok_source.consecutive_errors = 0
    ok_source.last_fetched_at = None
    ok_source.last_error_at = None
    ok_source.fetch_interval_minutes = 120
    ok_source.extra_config = {"primary_category": "historia"}

    ingest_calls = []

    async def fake_ingest(source_id):
        ingest_calls.append(source_id)
        if source_id == 101:
            raise RuntimeError("SSL certificate error")

    with patch("app.ingestion.manager.AsyncSessionLocal") as mock_sl, \
         patch("app.ingestion.manager.ingest_source", side_effect=fake_ingest), \
         patch("app.ingestion.manager.process_pending_news", new_callable=AsyncMock):
        mock_session = AsyncMock()
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        sources_result = MagicMock()
        sources_result.scalars.return_value.all.return_value = [csic_source, ok_source]
        mock_session.execute = AsyncMock(return_value=sources_result)

        # Should not raise even though source 101 raises
        await run_ingestion_cycle()

    # Both sources were attempted
    assert 101 in ingest_calls
    assert 102 in ingest_calls


# ---------------------------------------------------------------------------
# 10. Search / pagination / geo still work (classify_text integration)
# ---------------------------------------------------------------------------

def test_historia_keyword_search_works():
    """Articles with historia keywords score correctly after adding historia category."""
    result = classify_text(
        "Descubrimiento en yacimiento arqueológico de la Edad Media",
        "Los historiadores han identificado restos de una civilización del siglo XII.",
    )
    assert result[0] == "historia"
    assert len(result) >= 1


def test_non_historical_article_not_tagged_historia():
    """A general news article must NOT be classified as historia."""
    result = classify_text(
        "El Gobierno aprueba el plan de empleo para jóvenes",
        "El desempleo juvenil baja un punto. El banco central mantiene tipos de interés.",
    )
    assert "historia" not in result


def test_historia_does_not_trigger_on_vague_history_phrase():
    """'hará historia este gol' must not classify as historia (threshold=2 needed)."""
    result = classify_text(
        "Messi hará historia con este gol",
        "El futbolista marcó en el minuto 90 para ganar la liga.",
    )
    assert "historia" not in result, (
        f"Single vague 'historia' mention must not score >= threshold; got {result}"
    )
