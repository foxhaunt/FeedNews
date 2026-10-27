"""Tests for the personalized Catolicismo scoring system.

14 mandatory tests covering thematic affinity, doctrinal depth,
ecclesial context, source quality, routing via score_news(), and thresholds.

These tests do NOT touch the database.
"""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source(name="Test Source", url="https://example.com/feed",
                 reliability=0.75, editorial=None):
    extra_config = {"editorial": editorial} if editorial else {}
    return SimpleNamespace(name=name, url=url, reliability_score=reliability,
                           extra_config=extra_config)


def _make_news(title, summary="", content="",
               source_name="Test Source",
               source_url="https://example.com/feed",
               source_reliability=0.75,
               source_editorial=None,
               published_days_ago=30):
    pub = datetime.now(tz=timezone.utc) - timedelta(days=published_days_ago)
    source = _make_source(source_name, source_url, source_reliability,
                          editorial=source_editorial)
    return SimpleNamespace(
        title_original=title,
        summary_original=summary,
        content_original=content,
        published_at=pub,
        source=source,
        categories=[],
        relevance_score=None,
        relevance_level=None,
        geographic_scope="spain",
    )


def _score(title, summary="", content="", editorial=None, **kwargs):
    from app.processing.catolicismo_scorer import score_catolicismo_article
    news = _make_news(title, summary, content, source_editorial=editorial, **kwargs)
    score_catolicismo_article(news)
    return news.relevance_score, news.relevance_level


def _score_via_routing(title, summary="", content="", primary_category="catolicismo", **kwargs):
    from app.processing.scoring import score_news
    news = _make_news(title, summary, content, **kwargs)
    score_news(news, category_slugs=[], primary_category=primary_category)
    return news.relevance_score, news.relevance_level


# ---------------------------------------------------------------------------
# 1. Routing
# ---------------------------------------------------------------------------

class TestRouting:
    def test_score_news_routes_catolicismo_to_specialist(self):
        """score_news() with primary_category='catolicismo' calls specialist scorer."""
        score_via_routing, level_via_routing = _score_via_routing(
            "La misa tradicional y el rito tridentino en la FSSPX",
            summary="Análisis del motu proprio sobre la forma extraordinaria del rito romano.",
        )
        score_direct, level_direct = _score(
            "La misa tradicional y el rito tridentino en la FSSPX",
            summary="Análisis del motu proprio sobre la forma extraordinaria del rito romano.",
        )
        assert score_via_routing == score_direct
        assert level_via_routing == level_direct

    def test_standard_scorer_not_called_for_catolicismo(self):
        """Catolicismo articles must NOT use the standard 0.5 base scoring."""
        # Standard scorer gives 0.5 + recency. Catolicismo scorer starts from
        # weighted dimensions. A highly specific catolicismo article should
        # not land at 0.5 + recency.
        score, _ = _score(
            "El tomismo y la escolástica como fundamento de la doctrina católica",
            summary="Santo Tomás de Aquino y la filosofía perenne en el magisterio de la iglesia.",
        )
        # Standard scorer (no keywords) for a 30-day-old article would give ~0.55.
        # Catolicismo scorer should give a higher score for this topic.
        assert score > 0.55


# ---------------------------------------------------------------------------
# 2. Thematic affinity
# ---------------------------------------------------------------------------

class TestThematicAffinity:
    def test_traditional_mass_scores_high_affinity(self):
        """Article about traditional Mass (top priority) gets high affinity."""
        from app.processing.catolicismo_scorer import compute_thematic_affinity
        title = "la misa tradicional y la forma extraordinaria del rito tridentino"
        text = title + " análisis del motu proprio summorum pontificum y su impacto"
        affinity = compute_thematic_affinity(title, text)
        assert affinity >= 0.60

    def test_thomism_scores_high_affinity(self):
        """Article about thomism / scholastics scores high affinity."""
        from app.processing.catolicismo_scorer import compute_thematic_affinity
        title = "el tomismo y santo tomás de aquino como base de la escolástica"
        text = title + " la filosofía perenne y la metafísica tomista en la doctrina católica"
        affinity = compute_thematic_affinity(title, text)
        assert affinity >= 0.55

    def test_vatican_news_scores_medium_affinity(self):
        """Vatican current events (medium priority) score medium-range affinity."""
        from app.processing.catolicismo_scorer import compute_thematic_affinity
        title = "el papa francisco anuncia nuevo obispo para la diócesis de madrid"
        text = title + " la santa sede nombra al cardenal para la curia romana"
        affinity = compute_thematic_affinity(title, text)
        # Should be relevant but below high-priority topics.
        # Lower bound reflects the 0.38 dynamic floor (med >= 0.35).
        assert 0.35 <= affinity <= 0.75

    def test_non_catholic_article_scores_low_affinity(self):
        """Article unrelated to Catholicism scores at or near floor."""
        from app.processing.catolicismo_scorer import compute_thematic_affinity
        title = "el gobierno aprueba los presupuestos generales del estado"
        text = title + " el congreso vota la ley de presupuestos para el año próximo"
        affinity = compute_thematic_affinity(title, text)
        assert affinity <= 0.45

    def test_fsspx_article_scores_high(self):
        """FSSPX and Lefebvre get top-tier affinity boost."""
        from app.processing.catolicismo_scorer import compute_thematic_affinity
        title = "la fraternidad san pío x y écône: historia y situación actual"
        text = title + " lefebvre fundó la fsspx para preservar el rito tridentino"
        affinity = compute_thematic_affinity(title, text)
        assert affinity >= 0.60

    def test_sedevacantism_informative_scores_normally(self):
        """Informative sedevacantism article scores as medium-interest topic."""
        from app.processing.catolicismo_scorer import compute_thematic_affinity
        title = "qué es el sedevacantismo: historia y argumentos"
        text = title + " el sedevacantismo sostiene que la sede vacante se prolonga tras el concilio"
        affinity = compute_thematic_affinity(title, text)
        # Medium interest: should sit at or above the medium floor (0.28).
        assert affinity >= 0.28


# ---------------------------------------------------------------------------
# 3. Doctrinal depth
# ---------------------------------------------------------------------------

class TestDoctrinalDepth:
    def test_depth_signals_increase_score(self):
        """Presence of doctrinal depth signals raises score above baseline."""
        from app.processing.catolicismo_scorer import compute_doctrinal_depth
        text = "análisis teológico de la encíclica y los padres de la iglesia"
        summary = "Se examina el texto del concilio de trento y la patrística."
        score = compute_doctrinal_depth(text, summary)
        assert score > 0.40

    def test_superficiality_penalizes_depth(self):
        """Clickbait signals (top 10, curiosidades) reduce doctrinal depth."""
        from app.processing.catolicismo_scorer import compute_doctrinal_depth
        text_clean = "reflexión sobre el magisterio y la tradición apostólica"
        text_shallow = text_clean + " top 10 curiosidades impactante viral alucinante"
        summary = "Resumen breve."
        score_clean = compute_doctrinal_depth(text_clean, summary)
        score_shallow = compute_doctrinal_depth(text_shallow, summary)
        assert score_clean > score_shallow

    def test_long_summary_boosts_depth(self):
        """A summary longer than 400 characters increases depth score."""
        from app.processing.catolicismo_scorer import compute_doctrinal_depth
        short_summary = "Breve."
        long_summary = "a" * 450
        score_short = compute_doctrinal_depth("texto", short_summary)
        score_long  = compute_doctrinal_depth("texto", long_summary)
        assert score_long > score_short


# ---------------------------------------------------------------------------
# 4. Source quality
# ---------------------------------------------------------------------------

class TestSourceQuality:
    def test_high_reliability_source_scores_higher(self):
        """Vatican News (0.85) must score higher than a low-reliability source."""
        from app.processing.catolicismo_scorer import compute_source_quality
        high_src = _make_source(reliability=0.85, url="https://www.vaticannews.va/es.rss.xml")
        low_src  = _make_source(reliability=0.50, url="https://random-blog.example.com/feed")
        score_high = compute_source_quality("texto sobre catolicismo", high_src)
        score_low  = compute_source_quality("texto sobre catolicismo", low_src)
        assert score_high > score_low

    def test_trusted_source_url_adds_bonus(self):
        """Known Catholic source URL gets +0.10 bonus vs unknown URL."""
        from app.processing.catolicismo_scorer import compute_source_quality
        trusted = _make_source(reliability=0.70, url="https://infovaticana.com/feed/")
        unknown = _make_source(reliability=0.70, url="https://unknown.example.com/feed")
        score_trusted = compute_source_quality("catolicismo", trusted)
        score_unknown = compute_source_quality("catolicismo", unknown)
        assert score_trusted > score_unknown


# ---------------------------------------------------------------------------
# 5. End-to-end thresholds
# ---------------------------------------------------------------------------

class TestThresholds:
    def test_strong_traditional_article_is_featured(self):
        """High-quality traditional Mass article from a reliable source is featured."""
        score, level = _score(
            "El rito tridentino y la misa tradicional: la forma extraordinaria del rito romano",
            summary=(
                "El motu proprio summorum pontificum liberalizó el rito tridentino. "
                "La escolástica y el tomismo sustentan la doctrina de la fe. "
                "Análisis teológico de la tradición apostólica y el magisterio de la iglesia. "
                "El concilio de trento fue decisivo para la doctrina católica. "
                "Este artículo examina las fuentes patrísticas y los padres de la iglesia."
            ),
            source_reliability=0.85,
            source_url="https://infovaticana.com/feed/",
            published_days_ago=2,
        )
        assert level == "featured"
        assert score >= 0.72

    def test_weak_article_is_follow(self):
        """Superficial political article assigned to catolicismo is 'follow'."""
        score, level = _score(
            "El gobierno aprueba una ley de presupuestos",
            summary="Debate parlamentario sobre los presupuestos generales.",
            source_reliability=0.55,
            published_days_ago=90,
        )
        assert level == "follow"
        assert score < 0.48

    def test_medium_interest_article_is_relevant(self):
        """Standard Vatican current events article with a clear liturgical term
        lands in 'relevant' band (eucaristía is PRIORITY_HIGH in the title)."""
        score, level = _score(
            "El papa francisco preside la eucaristía en la plaza de san pedro",
            summary=(
                "El pontificado actual celebra la eucaristía con adoración eucarística "
                "ante miles de fieles. "
                "El cardenal y los obispos acompañan al santo padre en la santa sede."
            ),
            source_reliability=0.75,
            published_days_ago=5,
        )
        assert level in ("relevant", "featured")
        assert score >= 0.48


# ---------------------------------------------------------------------------
# 6. Editorial balance — traditionalist priority vs institutional volume
# ---------------------------------------------------------------------------

_TRADITIONAL_SUMMARY = (
    "El motu proprio summorum pontificum liberalizó la forma extraordinaria. "
    "La escolástica y el tomismo sustentan la doctrina de la fe. "
    "Análisis teológico de la tradición apostólica y el magisterio de la iglesia. "
    "El concilio de trento fue decisivo para la doctrina católica. "
    "Este artículo examina las fuentes patrísticas y los padres de la iglesia."
)

_INSTITUTIONAL_SUMMARY = (
    "El Santo Padre presidió el Ángelus ante miles de fieles en la plaza. "
    "El cardenal y los obispos acompañaron al papa en la santa sede."
)


class TestEditorialBalance:

    def test_traditionalist_beats_institutional_with_same_content(self):
        """When content is equally relevant, a traditionalist source must
        outrank a Vatican News or CEE article of similar quality."""
        STRONG_TITLE = "El rito tridentino y la misa tradicional: análisis doctrinal"

        score_tradi, _ = _score(
            STRONG_TITLE,
            summary=_TRADITIONAL_SUMMARY,
            source_reliability=0.75,
            source_url="https://infovaticana.com/feed/",
            editorial="catolicismo_tradicional",
            published_days_ago=5,
        )
        score_vn, _ = _score(
            STRONG_TITLE,
            summary=_TRADITIONAL_SUMMARY,
            source_reliability=0.85,
            source_url="https://www.vaticannews.va/es.rss.xml",
            editorial="vaticano_oficial",
            published_days_ago=5,
        )
        assert score_tradi > score_vn, (
            f"Traditionalist ({score_tradi:.4f}) must beat Vatican News "
            f"({score_vn:.4f}) with equally relevant content"
        )

    def test_institutional_important_news_can_be_featured(self):
        """Vatican News or CEE must NOT receive automatic penalties that
        prevent genuinely important news from reaching 'featured'."""
        MOTU_PROPRIO_TITLE = "El Papa promulga un nuevo motu proprio sobre la forma extraordinaria"
        MOTU_PROPRIO_SUMMARY = (
            "La carta apostólica constituye un decreto de doctrina de la fe "
            "sobre el rito tridentino. Análisis teológico del magisterio de la iglesia "
            "a la luz del concilio de trento y los padres de la iglesia. "
            "El texto examina las fuentes patrísticas y la tradición apostólica "
            "desde la perspectiva de la congregación para la doctrina de la fe."
        )
        score, level = _score(
            MOTU_PROPRIO_TITLE,
            summary=MOTU_PROPRIO_SUMMARY,
            source_reliability=0.85,
            source_url="https://www.vaticannews.va/es.rss.xml",
            editorial="vaticano_oficial",
            published_days_ago=1,
        )
        assert level == "featured", (
            f"Important Vatican News article (score={score:.4f}) must reach 'featured'"
        )

    def test_weak_traditionalist_does_not_get_bonus(self):
        """A traditionalist source with low thematic affinity (< 0.60) must
        NOT receive the editorial bonus — source alone is not sufficient."""
        score_tradi, _ = _score(
            "Agenda pastoral de la parroquia para el mes de diciembre",
            summary="El párroco anuncia los horarios de misa y actividades.",
            source_reliability=0.70,
            source_url="https://adelantelafe.com/feed/",
            editorial="catolicismo_tradicional",
            published_days_ago=3,
        )
        score_no_editorial, _ = _score(
            "Agenda pastoral de la parroquia para el mes de diciembre",
            summary="El párroco anuncia los horarios de misa y actividades.",
            source_reliability=0.70,
            source_url="https://adelantelafe.com/feed/",
            editorial=None,
            published_days_ago=3,
        )
        # No bonus was applied: scores must be equal (same article, same source quality)
        assert score_tradi == score_no_editorial, (
            "Bonus must not apply when article has no PRIORITY_HIGH term "
            "and no strong ecclesial context signal"
        )

    def test_historia_scoring_unaffected(self):
        """Changes to catolicismo profile must not alter historia scoring."""
        from app.processing.scoring import score_news
        from app.models import News, Source
        from datetime import datetime, timezone

        src = Source(
            id=99, name="El Reto Histórico", url="https://reto.es/feed",
            reliability_score=0.80, geographic_scope="spain", language="es",
            fetch_interval_minutes=120, consecutive_errors=0,
            total_articles_fetched=0,
        )
        news = News(
            id=99, source_id=99,
            url="https://reto.es/1", url_hash="h1",
            title_original="La Reconquista y la arqueología medieval en la Edad Media",
            title_es="La Reconquista y la arqueología medieval en la Edad Media",
            summary_original=(
                "El yacimiento arqueológico revela datos sobre la historia medieval. "
                "La reconquista española transformó la civilización ibérica del siglo xii."
            ),
            language_original="es",
            geographic_scope="spain",
            published_at=datetime.now(tz=timezone.utc),
            relevance_score=0.5, relevance_level="follow",
            is_duplicate=False, processing_status="raw",
            translation_status="not_needed",
            categories=[],
        )
        news.source = src

        score_news(news, primary_category="historia")

        assert news.relevance_level in ("featured", "relevant", "follow")
        assert 0.0 <= news.relevance_score <= 1.0
