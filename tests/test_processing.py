"""Tests for scoring, deduplication, and categorization."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


def make_news(title, geo="international", score=0.5, level="follow", published=None, id=1):
    from app.models import News, Source
    src = Source(id=1, name="Test Source", url="https://test.com/rss", reliability_score=0.9,
                 geographic_scope=geo, language="es", fetch_interval_minutes=30,
                 consecutive_errors=0, total_articles_fetched=0)
    n = News(
        id=id,
        source_id=1,
        url=f"https://example.com/{id}",
        url_hash=f"hash{id}",
        title_original=title,
        title_es=title,
        summary_original="Resumen de prueba para la noticia.",
        language_original="es",
        geographic_scope=geo,
        published_at=published or datetime.now(tz=timezone.utc),
        relevance_score=score,
        relevance_level=level,
        is_duplicate=False,
        processing_status="raw",
        translation_status="not_needed",
        categories=[],
    )
    n.source = src
    return n


# ---- Scoring ----
def test_score_fresh_news_gets_high_score():
    from app.processing.scoring import score_news
    news = make_news("Gobierno declara estado de emergencia nacional", geo="spain")
    score_news(news)
    assert news.relevance_score > 0.5


def test_score_old_news_gets_lower_score():
    from app.processing.scoring import score_news
    old = datetime.now(tz=timezone.utc) - timedelta(days=10)
    news = make_news("Ordinary article about weather", published=old)
    score_news(news)
    assert news.relevance_level in ("follow", "relevant")


def test_score_high_impact_keywords_boost():
    from app.processing.scoring import score_news
    n1 = make_news("Nuevo programa de salud")
    n2 = make_news("Guerra y ataque en zona de conflicto")
    score_news(n1)
    score_news(n2)
    assert n2.relevance_score > n1.relevance_score


def test_score_levels():
    from app.processing.scoring import score_news
    news = make_news("Atentado terrorista causa decenas de muertos y heridos en ciudad importante")
    score_news(news)
    assert news.relevance_level in ("featured", "relevant", "follow")


def test_score_tier1_beats_tier2():
    """Tier-1 high-impact keywords should raise the score more than tier-2 common ones."""
    from app.processing.scoring import score_news
    n_tier1 = make_news("Bomba destruye edificio, decenas de muertos en el ataque")
    n_tier2 = make_news("Elecciones presidenciales: acuerdo entre partidos tras la crisis")
    n_tier2.published_at = n_tier1.published_at  # same freshness
    score_news(n_tier1)
    score_news(n_tier2)
    assert n_tier1.relevance_score > n_tier2.relevance_score


def test_score_low_reliability_not_zero():
    """Even a low-reliability source (0.45) should not push score to zero."""
    from app.processing.scoring import score_news
    from app.models import Source
    news = make_news("Noticia reciente con información relevante")
    news.source = Source(
        id=99, name="Fuente Baja", url="https://baja.com/rss",
        reliability_score=0.45, geographic_scope="spain", language="es",
        fetch_interval_minutes=30, consecutive_errors=0, total_articles_fetched=0,
    )
    score_news(news)
    assert news.relevance_score > 0.1


def test_score_category_slugs_applied():
    """Passing category_slugs should use the defensa multiplier."""
    from app.processing.scoring import score_news
    old_date = __import__('datetime').datetime.now(tz=__import__('datetime').timezone.utc) - __import__('datetime').timedelta(days=5)
    n_no_cat = make_news("Noticia genérica", published=old_date)
    n_defensa = make_news("Noticia genérica", published=old_date)
    score_news(n_no_cat, category_slugs=[])
    score_news(n_defensa, category_slugs=["defensa"])
    assert n_defensa.relevance_score > n_no_cat.relevance_score


# ── Geographic classification ────────────────────────────────────────────────

class GeoCase:
    def __init__(self, title, summary, expected, description=""):
        self.title = title
        self.summary = summary
        self.expected = expected
        self.description = description


GEO_CASES = [
    GeoCase("Decisión del Gobierno de España sobre pensiones",
            "El ejecutivo español anunció medidas", "spain",
            "Gobierno español → spain"),
    GeoCase("Spanish government announces austerity plan",
            "The government of España cuts spending", "spain",
            "English title but Spain content → spain"),
    GeoCase("Operación policial en Madrid detiene a veinte personas",
            "La Guardia Civil llevó a cabo la operación", "spain",
            "Madrid + Guardia Civil → spain"),
    GeoCase("Brasil decide entregar todo el poder a Bolsonaro",
            "La segunda vuelta presidencial se celebró en Brasilia", "international",
            "Brazil article in Spanish → international (not spain)"),
    GeoCase("Voters in Brazil to choose between Lula and Bolsonaro's son",
            "Brazil election second round", "international",
            "Brazil election in English → international"),
    GeoCase("Elecciones en Francia: Macron convoca segunda vuelta",
            "El presidente francés disuelve la Asamblea Nacional", "europe",
            "France elections → europe"),
    GeoCase("European Parliament votes on AI regulation",
            "Members of the European Parliament approved the bill", "europe",
            "EU Parliament → europe"),
    GeoCase("Crisis política en Argentina: el Congreso debate el presupuesto",
            "El Senado argentino aprobó la ley de presupuesto", "international",
            "Argentina Congreso+Senado → international (not spain)"),
    GeoCase("BCE sube los tipos de interés al 4,5 por ciento",
            "El Banco Central Europeo anunció la medida en Fráncfort", "europe",
            "BCE + Banco Central Europeo → europe"),
    GeoCase("Soldiers guard center of Milan as protesters march across Europe",
            "Thousands march in European cities against austerity", "europe",
            "Milan + Europe → europe"),
    GeoCase("Earthquake strikes Turkey, dozens killed",
            "Search and rescue operations under way", "international",
            "Turkey earthquake → international (grey/turkey substring should not match spain)"),
    GeoCase("AFP boss says rhetoric fuels threats against MPs",
            "The head of AFP said heated rhetoric is threatening MPs", "international",
            "AFP 'pp' substring should not trigger spain"),
    GeoCase("Decisión estadounidense afecta a varios países de la OTAN",
            "España podría verse afectada entre otros aliados", "spain",
            "España mentioned → spain even in international context"),
]


def test_geo_classification_cases():
    from app.ingestion.normalizer import extract_geo_hints
    failures = []
    for case in GEO_CASES:
        hints = extract_geo_hints(case.title, case.summary)
        got = hints[0] if hints else "international"
        if got != case.expected:
            failures.append(
                f"FAIL [{case.description}]: expected={case.expected} got={got}\n"
                f"  title={case.title!r}"
            )
    if failures:
        raise AssertionError("\n" + "\n".join(failures))


def test_translation_does_not_change_geo_scope():
    """Translating a news item must NOT affect its geographic_scope."""
    from app.ingestion.normalizer import extract_geo_hints
    title_en = "Brazil elects new president in historic second round"
    summary_en = "Lula da Silva wins the election in São Paulo"
    title_es = "Brasil elige nuevo presidente en segunda vuelta histórica"
    summary_es = "Lula da Silva gana las elecciones en São Paulo"

    geo_en = extract_geo_hints(title_en, summary_en)[0]
    geo_es = extract_geo_hints(title_es, summary_es)[0]
    # Same event regardless of language
    assert geo_en == geo_es == "international"


def test_spain_specific_terms_work():
    from app.ingestion.normalizer import extract_geo_hints
    assert extract_geo_hints("El PSOE pierde escaños en el Congreso de los Diputados", None)[0] == "spain"
    assert extract_geo_hints("Feijóo critica al gobierno en el Senado español", None)[0] == "spain"
    assert extract_geo_hints("Moncloa convoca una rueda de prensa urgente", None)[0] == "spain"


def test_generic_words_dont_trigger_spain():
    """'congreso', 'senado', 'rey', 'pp', 'podemos' alone must NOT trigger spain."""
    from app.ingestion.normalizer import extract_geo_hints
    # These appear in non-Spanish political journalism
    assert extract_geo_hints("El Congreso de Brasil aprobó la ley", None)[0] != "spain"
    assert extract_geo_hints("El Senado de Argentina debate el presupuesto", None)[0] != "spain"
    assert extract_geo_hints("El rey de los negocios de Silicon Valley", None)[0] != "spain"
    assert extract_geo_hints("The PP factor in Australian politics", None)[0] != "spain"


def test_reclassify_changes_wrong_scope():
    """reclassify_geo should reassign international articles wrongly tagged as spain."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch
    from datetime import datetime, timezone
    from app.models import News

    # Simulate article about Brazil stored as "spain"
    row = MagicMock()
    row.id = 28
    row.title_original = "Brasil decide entregar todo el poder a Bolsonaro"
    row.summary_original = "Segunda vuelta presidencial en Brasil"
    row.geographic_scope = "spain"   # wrong

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    async def run():
        from app.processing.reclassify import reclassify_geo
        result = await reclassify_geo(mock_session, limit=10)
        return result

    result = asyncio.run(run())
    assert result["changed"] >= 1
    assert "international" in result["by_scope"]


# ---- Deduplication ----
def test_word_overlap_identical_titles():
    from app.processing.deduplication import _word_overlap_score
    score = _word_overlap_score("El gobierno aprueba el presupuesto", "El gobierno aprueba el presupuesto")
    assert score == 1.0


def test_word_overlap_completely_different():
    from app.processing.deduplication import _word_overlap_score
    score = _word_overlap_score("Elecciones en España resultados", "Terremoto devasta costa pacífico")
    assert score < 0.2


def test_word_overlap_similar_titles():
    from app.processing.deduplication import _word_overlap_score
    score = _word_overlap_score(
        "El gobierno español aprueba nuevos presupuestos generales",
        "El gobierno aprueba los presupuestos generales del estado"
    )
    assert score >= 0.4


def test_normalize_title_removes_stopwords():
    from app.processing.deduplication import _normalize_title
    normalized = _normalize_title("El gobierno de España aprueba la ley")
    assert "el" not in normalized.split()
    assert "la" not in normalized.split()
    assert "gobierno" in normalized


# ---- Language detection ----
def test_detect_spanish():
    from app.translation.detector import detect_language
    lang = detect_language("El gobierno español ha aprobado los nuevos presupuestos generales del Estado.")
    assert lang == "es"


def test_detect_english():
    from app.translation.detector import detect_language
    lang = detect_language("The government has announced new economic measures to boost growth.")
    assert lang == "en"


def test_detect_short_text_returns_none():
    from app.translation.detector import detect_language
    lang = detect_language("Hi")
    assert lang is None


def test_detect_returns_none_on_error():
    from app.translation.detector import detect_language
    with patch("langdetect.detect", side_effect=Exception("fail")):
        result = detect_language("Some text that should cause an error")
        assert result is None
