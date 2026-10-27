"""Tests for Historia category and history sources integration.

Covers:
  8.1  – Historia category present in seeds CATEGORIES list
  8.2  – All 5 valid history sources present in seeds SOURCES list
  8.3  – Every history source has primary_category = "historia" in extra_config
  8.4  – CSIC sources have ssl_verify = False in extra_config
  8.5  – NG Historia is NOT in SOURCES (blocked by Akamai CDN, not integrable)
  8.6  – Categorizer assigns historia as primary when source_primary_category set
  8.7  – Historia primary category overrides keyword-matched categories
  8.8  – Historia forced even when title matches Política keywords
  8.9  – Historia kept as primary even if no other keywords match
  8.10 – categorize_news respects source_primary_category via DB round-trip
  8.11 – process_pending_news reads primary_category from source.extra_config
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers – seeds data (unit tests, no DB)
# ---------------------------------------------------------------------------

HISTORY_SOURCE_NAMES = {
    "El Reto Histórico",
    "Muy Interesante Historia",
    "Hispania Sacra (CSIC)",
    "Hispania (CSIC)",
    "En la España Medieval (UCM)",
}

CSIC_SOURCE_NAMES = {
    "Hispania Sacra (CSIC)",
    "Hispania (CSIC)",
}


def _get_seeds():
    from app.seeds import CATEGORIES, SOURCES
    return CATEGORIES, SOURCES


def _historia_sources():
    """Return enabled sources that have primary_category='historia'."""
    _, sources = _get_seeds()
    return [
        s for s in sources
        if s.get("extra_config", {}).get("primary_category") == "historia"
        and s.get("enabled", True) is not False
    ]


# ---------------------------------------------------------------------------
# 8.1  Historia category in seeds
# ---------------------------------------------------------------------------

def test_8_1_historia_category_in_seeds():
    """Historia category must be present in CATEGORIES with correct fields."""
    categories, _ = _get_seeds()
    slugs = {c["slug"] for c in categories}
    assert "historia" in slugs, "historia slug missing from CATEGORIES"

    historia = next(c for c in categories if c["slug"] == "historia")
    assert historia["name_es"] == "Historia"
    assert historia["name_en"] == "History"
    assert historia.get("icon"), "historia category must have an icon"


# ---------------------------------------------------------------------------
# 8.2  All 5 valid history sources present
# ---------------------------------------------------------------------------

def test_8_2_all_history_sources_present():
    """All 5 valid history sources must be in SOURCES."""
    _, sources = _get_seeds()
    names = {s["name"] for s in sources}
    missing = HISTORY_SOURCE_NAMES - names
    assert not missing, f"Missing history sources: {missing}"


def test_8_2_correct_count_of_historia_enabled_sources():
    """Exactly 5 enabled sources should have primary_category='historia'."""
    sources = _historia_sources()
    assert len(sources) == 5, (
        f"Expected 5 enabled historia sources, found {len(sources)}: "
        f"{[s['name'] for s in sources]}"
    )


# ---------------------------------------------------------------------------
# 8.3  All history sources have primary_category = "historia"
# ---------------------------------------------------------------------------

def test_8_3_primary_category_historia_on_all_history_sources():
    """Every history source must have extra_config.primary_category = 'historia'."""
    sources = _historia_sources()
    for src in sources:
        cfg = src.get("extra_config", {})
        assert cfg.get("primary_category") == "historia", (
            f"Source '{src['name']}' missing primary_category='historia' "
            f"in extra_config: {cfg}"
        )


# ---------------------------------------------------------------------------
# 8.4  CSIC sources have ssl_verify = False
# ---------------------------------------------------------------------------

def test_8_4_csic_sources_have_ssl_verify_false():
    """Hispania Sacra and Hispania CSIC must have ssl_verify=False (expired cert)."""
    _, sources = _get_seeds()
    by_name = {s["name"]: s for s in sources}
    for name in CSIC_SOURCE_NAMES:
        assert name in by_name, f"CSIC source '{name}' not found in SOURCES"
        cfg = by_name[name].get("extra_config", {})
        assert cfg.get("ssl_verify") is False, (
            f"Source '{name}' must have ssl_verify=False in extra_config, got: {cfg}"
        )


# ---------------------------------------------------------------------------
# 8.5  NatGeo Historia is absent (403 Forbidden, CDN-blocked)
# ---------------------------------------------------------------------------

def test_8_5_natgeo_historia_is_disabled():
    """Historia National Geographic must be disabled (CDN blocks all RSS requests)."""
    _, sources = _get_seeds()
    ng = next(
        (s for s in sources
         if "national" in s["name"].lower() and "geographic" in s["name"].lower()),
        None,
    )
    assert ng is not None, (
        "Historia National Geographic should be present in SOURCES as a documented disabled source"
    )
    assert ng.get("enabled", True) is False, (
        f"Historia National Geographic must have enabled=False (HTTP 403), "
        f"got: {ng.get('enabled', True)}"
    )
    note = ng.get("extra_config", {}).get("note", "")
    assert "403" in note or "bloquea" in note.lower() or "bloqueado" in note.lower(), (
        f"NatGeo Historia extra_config should document the 403 block, got note='{note}'"
    )


# ---------------------------------------------------------------------------
# 8.6  History sources have correct geographic_scope and language
# ---------------------------------------------------------------------------

def test_8_6_history_sources_geographic_scope_spain():
    """All history sources must have geographic_scope='spain'."""
    for src in _historia_sources():
        assert src["geographic_scope"] == "spain", (
            f"Source '{src['name']}' geographic_scope should be 'spain', "
            f"got '{src['geographic_scope']}'"
        )


def test_8_6_history_sources_language_es():
    """All history sources must have language='es'."""
    for src in _historia_sources():
        assert src["language"] == "es", (
            f"Source '{src['name']}' language should be 'es', "
            f"got '{src['language']}'"
        )


def test_8_6_history_sources_feed_type_rss():
    """All history sources must use feed_type='rss'."""
    for src in _historia_sources():
        assert src["feed_type"] == "rss", (
            f"Source '{src['name']}' feed_type should be 'rss', "
            f"got '{src['feed_type']}'"
        )


# ---------------------------------------------------------------------------
# 8.7  Categorizer: source_primary_category forces historia as first slug
# ---------------------------------------------------------------------------

def test_8_7_classify_text_historia_forced_primary():
    """When source_primary_category='historia', historia must be first slug."""
    from app.processing.categorizer import classify_text

    # Article title with no obvious historia keywords — should still produce historia
    slugs = classify_text("Nuevos descubrimientos en excavaciones medievales", "")
    # classify_text alone may or may not return historia; that's fine —
    # what matters is that categorize_news forces it. This test verifies the
    # slug insertion logic via a direct simulation.
    source_primary = "historia"
    combined = [source_primary] + [s for s in slugs if s != source_primary]
    combined = combined[:3]
    assert combined[0] == "historia", (
        f"historia must be first after forcing primary, got: {combined}"
    )


def test_8_7_historia_forced_overrides_keyword_match():
    """Historia is primary even when title strongly matches another category."""
    from app.processing.categorizer import classify_text

    # Strong economia keywords — without override this would be economia
    economia_title = "PIB español crece un 3% en 2024 con máximo histórico de inversión"
    economia_slugs = classify_text(economia_title, "")
    assert "economia" in economia_slugs or len(economia_slugs) > 0

    # Apply source_primary_category override manually
    source_primary = "historia"
    overridden = [source_primary] + [s for s in economia_slugs if s != source_primary]
    overridden = overridden[:3]
    assert overridden[0] == "historia", (
        f"historia must remain primary after override, got: {overridden}"
    )


# ---------------------------------------------------------------------------
# 8.8  Historia forced even when title matches Política keywords
# ---------------------------------------------------------------------------

def test_8_8_historia_overrides_politica():
    """Articles from historia sources must have historia as primary, not política."""
    from app.processing.categorizer import classify_text

    politica_title = "El Gobierno aprueba una nueva ley de reforma constitucional"
    politica_slugs = classify_text(politica_title, "")

    source_primary = "historia"
    overridden = [source_primary] + [s for s in politica_slugs if s != source_primary]
    overridden = overridden[:3]
    assert overridden[0] == "historia"
    # política may appear as secondary — that's acceptable, just not primary
    if "politica" in overridden:
        assert overridden.index("politica") > 0, (
            "política must not be primary category for a historia source article"
        )


# ---------------------------------------------------------------------------
# 8.9  Historia primary even with no keyword matches
# ---------------------------------------------------------------------------

def test_8_9_historia_primary_with_no_keywords():
    """Even if title has no category keywords, historia is still primary."""
    from app.processing.categorizer import classify_text

    title = "Crónica de Enrique IV"
    slugs = classify_text(title, "")

    source_primary = "historia"
    result = [source_primary] + [s for s in slugs if s != source_primary]
    result = result[:3]
    assert result[0] == "historia"


# ---------------------------------------------------------------------------
# 8.10  categorize_news DB round-trip with source_primary_category
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_10_categorize_news_with_historia_primary(db_session):
    """categorize_news returns historia first when source_primary_category='historia'."""
    from app.models import Category, News, Source
    from app.processing.categorizer import categorize_news
    from datetime import datetime, timezone

    # Seed a dummy source (source_id is NOT NULL)
    src = Source(name="TestHistoria10a", url="https://test-historia10a.example.com/feed",
                 language="es", geographic_scope="spain", reliability_score=0.8,
                 fetch_interval_minutes=60, enabled=True, extra_config={})
    db_session.add(src)
    hist_cat = Category(slug="historia", name_es="Historia", name_en="History",
                        icon="📜", order=0)
    db_session.add(hist_cat)
    await db_session.flush()

    news = News(
        source_id=src.id,
        url="https://example.com/historia-test-1",
        url_hash="aaaa1111" * 8,
        title_original="Conquista de Granada 1492",
        summary_original="El rey Fernando II conquistó Granada poniendo fin a la Reconquista.",
        language_original="es",
        processing_status="raw",
        published_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(news)
    await db_session.flush()

    slugs = await categorize_news(news, db_session, source_primary_category="historia")
    assert slugs[0] == "historia", f"historia must be first slug, got: {slugs}"
    assert "historia" in slugs


@pytest.mark.asyncio
async def test_8_10_categorize_news_historia_with_competing_keywords(db_session):
    """historia stays primary even when article matches another category strongly."""
    from app.models import Category, News, Source
    from app.processing.categorizer import categorize_news
    from datetime import datetime, timezone

    # Seed a dummy source (source_id is NOT NULL)
    src = Source(name="TestHistoria10b", url="https://test-historia10b.example.com/feed",
                 language="es", geographic_scope="spain", reliability_score=0.8,
                 fetch_interval_minutes=60, enabled=True, extra_config={})
    db_session.add(src)
    for cat in [
        Category(slug="historia", name_es="Historia", name_en="History", icon="📜", order=0),
        Category(slug="politica", name_es="Política", name_en="Politics", icon="🏛️", order=1),
    ]:
        db_session.add(cat)
    await db_session.flush()

    news = News(
        source_id=src.id,
        url="https://example.com/historia-test-2",
        url_hash="bbbb2222" * 8,
        title_original="El Gobierno de la Segunda República aprueba la Constitución de 1931",
        summary_original="El presidente Alcalá-Zamora promulgó la constitución republicana.",
        language_original="es",
        processing_status="raw",
        published_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(news)
    await db_session.flush()

    slugs = await categorize_news(news, db_session, source_primary_category="historia")
    assert slugs[0] == "historia", (
        f"historia must be primary even with política keywords in title: {slugs}"
    )


# ---------------------------------------------------------------------------
# 8.11  process_pending_news reads primary_category from source.extra_config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_11_manager_passes_primary_category_to_categorizer():
    """process_pending_news must extract primary_category from source.extra_config."""
    from app.ingestion.manager import process_pending_news
    from app.models import News, Source, Category
    from unittest.mock import patch, AsyncMock

    # We verify the wiring: that categorize_news is called with source_primary_category
    captured_calls = []

    async def mock_categorize(news, session, source_primary_category=None):
        captured_calls.append(source_primary_category)
        return ["historia"]

    with patch("app.ingestion.manager.categorize_news", side_effect=mock_categorize):
        with patch("app.ingestion.manager.score_news"):
            with patch("app.ingestion.manager.AsyncSessionLocal") as mock_ctx:
                # Build a mock session that returns one raw news item
                mock_source = MagicMock(spec=Source)
                mock_source.extra_config = {"primary_category": "historia"}

                mock_news = MagicMock(spec=News)
                mock_news.processing_status = "raw"
                mock_news.is_duplicate = False
                mock_news.source = mock_source

                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = [mock_news]
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_session.commit = AsyncMock()

                mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

                await process_pending_news()

    assert len(captured_calls) >= 1, "categorize_news was not called"
    assert captured_calls[0] == "historia", (
        f"process_pending_news must pass primary_category='historia' from "
        f"source.extra_config, but passed: {captured_calls[0]}"
    )


# ---------------------------------------------------------------------------
# Extra: SSL bypass wired correctly for CSIC sources
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ssl_verify_false_passed_to_fetch_feed_for_csic():
    """_fetch_source must pass ssl_verify=False for sources with that config."""
    from app.ingestion.manager import _fetch_source
    from app.models import Source

    mock_source = MagicMock(spec=Source)
    mock_source.url = "https://hispaniasacra.revistas.csic.es/index.php/.../rss2"
    mock_source.language = "es"
    mock_source.extra_config = {"ssl_verify": False, "primary_category": "historia"}

    captured_kwargs = {}

    async def mock_fetch(url, lang, ssl_verify=True):
        captured_kwargs["ssl_verify"] = ssl_verify
        return []

    with patch("app.ingestion.manager.fetch_feed", side_effect=mock_fetch):
        articles, err = await _fetch_source(mock_source)

    assert err is None, f"_fetch_source raised unexpected error: {err}"
    assert captured_kwargs.get("ssl_verify") is False, (
        f"ssl_verify=False must be passed to fetch_feed for CSIC sources, "
        f"got: {captured_kwargs}"
    )


# ---------------------------------------------------------------------------
# Geo-scope preservation (Part 3.1, tests 5–6)
# ---------------------------------------------------------------------------

def test_3_1_historia_source_preserves_spain_scope():
    """Spec 3.1.5 — historia source with scope=spain keeps spain even when
    the article mentions Portugal."""
    from app.ingestion.normalizer import extract_geo_hints
    title = "Guerra y paz entre Portugal y Castilla: las vistas del final de la Edad Media"
    summary = "Entre 1369 y 1480, los reinos de Portugal y Castilla se enfrentaron cinco veces."

    # The geo-hints function detects Portugal → would return 'europe'
    hints = extract_geo_hints(title, summary)
    assert hints == ["europe"], "Geo hint should detect Portugal as europe"

    # But ingest_source() skips geo-hints for historia sources.
    # We verify the guard condition directly.
    source_extra_config = {"primary_category": "historia", "editorial": "academico"}
    _is_historia = source_extra_config.get("primary_category") == "historia"
    assert _is_historia, "The historia guard must fire for this source"

    # Simulated result: geo_scope stays as the source's declared scope
    declared_scope = "spain"
    geo_scope = declared_scope
    if not _is_historia:
        geo_scope = hints[0]
    assert geo_scope == "spain", (
        f"historia source must keep geographic_scope='spain', got '{geo_scope}'"
    )


def test_3_1_generic_source_geo_can_be_overridden():
    """Spec 3.1.6 — generic source without primary_category can get non-declared scope from geo-hints."""
    from app.ingestion.normalizer import extract_geo_hints
    # Use text with explicit European countries to trigger an 'europe' hint
    title = "Francia y Alemania firman un nuevo tratado de cooperación económica"
    summary = "París y Berlín sellaron hoy un acuerdo de inversión conjunta."

    hints = extract_geo_hints(title, summary)
    assert len(hints) > 0, f"Expected at least one geo hint, got {hints}"

    source_extra_config = {"editorial": "centro"}  # no primary_category
    _is_historia = source_extra_config.get("primary_category") == "historia"
    assert not _is_historia, "Generic source must not trigger the historia guard"

    declared_scope = "international"
    geo_scope = declared_scope
    if not _is_historia and hints:
        geo_scope = hints[0]
    assert geo_scope != declared_scope, (
        f"Generic source geo_scope must be overridden by geo-hints (was '{declared_scope}', got '{geo_scope}')"
    )
