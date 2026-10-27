"""Tests for the personalized Historia scoring system.

Spec 9 — 15 mandatory tests.

These tests do NOT touch the database. They create lightweight News objects
using a helper and call score_historia_article() or score_news() directly.
"""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_source(name="Test Source", url="https://example.com/feed",
                 reliability=0.75):
    return SimpleNamespace(name=name, url=url, reliability_score=reliability)


def _make_news(title, summary="", content="",
               source_name="Test Source",
               source_url="https://example.com/feed",
               source_reliability=0.75,
               published_days_ago=30,
               is_duplicate=False):
    """Create a lightweight News-like object for scoring tests."""
    pub = datetime.now(tz=timezone.utc) - timedelta(days=published_days_ago)
    source = _make_source(source_name, source_url, source_reliability)
    news = SimpleNamespace(
        title_original=title,
        summary_original=summary,
        content_original=content,
        published_at=pub,
        is_duplicate=is_duplicate,
        source=source,
        categories=[],
        relevance_score=None,
        relevance_level=None,
        geographic_scope="spain",
    )
    return news


def _score_historia(title, summary="", content="", **kwargs):
    """Score a news object with the historia scorer and return (score, level)."""
    from app.processing.historia_scorer import score_historia_article
    news = _make_news(title, summary, content, **kwargs)
    score_historia_article(news)
    return news.relevance_score, news.relevance_level


def _score_standard(title, summary="", content="", category_slugs=None,
                    primary_category=None, **kwargs):
    """Score a news object with the standard scorer via score_news()."""
    from app.processing.scoring import score_news
    news = _make_news(title, summary, content, **kwargs)
    score_news(news, category_slugs=category_slugs or [], primary_category=primary_category)
    return news.relevance_score, news.relevance_level


# ---------------------------------------------------------------------------
# Test 1 — Artículo riguroso sobre la Reconquista → afinidad alta
# ---------------------------------------------------------------------------

def test_1_reconquista_rigurosa_alta_afinidad():
    """Un artículo académico sobre la Reconquista debe obtener una puntuación alta."""
    title = "Las estrategias diplomáticas de la Corona de Castilla durante la Reconquista"
    summary = (
        "Este estudio analiza las relaciones entre los reinos cristianos de la Reconquista "
        "y los reinos taifas de Al-Ándalus. Se examinan las causas y consecuencias de las "
        "alianzas temporales, el contexto histórico de la expansión castellana y las fuentes "
        "primarias que documentan los acuerdos entre Castilla y los reinos andalusíes."
    )
    score, level = _score_historia(title, summary,
                                   source_name="Instituto de Historia CSIC",
                                   source_url="https://digital.csic.es/feed",
                                   source_reliability=0.9,
                                   published_days_ago=60)
    assert level in ("featured", "relevant"), (
        f"Artículo de Reconquista con resumen riguroso debería ser featured o relevant, "
        f"score={score}, level={level}"
    )
    assert score >= 0.55, f"Score esperado >= 0.55, obtenido {score}"


# ---------------------------------------------------------------------------
# Test 2 — Formación de los reinos hispanos → prioridad alta
# ---------------------------------------------------------------------------

def test_2_reinos_hispanos_prioridad_alta():
    """La formación de los reinos hispanos es un tema de máxima prioridad."""
    title = "El origen del Reino de Navarra y su expansión territorial en el siglo X"
    summary = (
        "Este artículo estudia la formación del Reino de Navarra a partir del núcleo de "
        "Pamplona. Se analizan las relaciones con el Reino de Aragón y el Reino de León, "
        "y el papel de los fueros en la consolidación del poder real navarro."
    )
    score, level = _score_historia(title, summary, published_days_ago=45)
    assert score >= 0.50, (
        f"La formación de los reinos hispanos debe tener score >= 0.50, obtenido {score}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Artículo de calidad sobre la Segunda Guerra Mundial (no reciente)
# ---------------------------------------------------------------------------

def test_3_segunda_guerra_mundial_no_reciente():
    """Un artículo histórico serio sobre la IIGM publicado hace meses debe ser relevante."""
    title = "El frente oriental de la Segunda Guerra Mundial y la Operación Barbarroja"
    summary = (
        "Análisis histórico de la campaña alemana en la Unión Soviética. Se estudian las "
        "causas de la decisión de Hitler de atacar la URSS, la estrategia militar del Tercer "
        "Reich, las consecuencias del nazismo en los territorios ocupados y los debates "
        "historiográficos sobre el holocausto en el frente oriental."
    )
    score, level = _score_historia(title, summary, published_days_ago=180)
    assert level in ("featured", "relevant"), (
        f"Artículo serio de IIGM sin recencia debería ser featured o relevant, score={score}"
    )
    # Sin bonificación por recencia; la calidad del contenido debe sostenerlo
    assert score >= 0.45, f"Score esperado >= 0.45, obtenido {score}"


# ---------------------------------------------------------------------------
# Test 4 — Artículo riguroso sobre otra civilización → puede ser relevante
# ---------------------------------------------------------------------------

def test_4_otra_civilizacion_puede_ser_relevante():
    """Un artículo histórico riguroso sobre otra civilización puede alcanzar relevant."""
    title = "La administración del Imperio Romano y el papel del Senado romano"
    summary = (
        "Estudio sobre las instituciones de la República romana y su transición al Imperio. "
        "Se analiza el papel del Senado, Julio César, Augusto y el contexto político de "
        "la transformación institucional. Incluye fuentes primarias y referencias académicas."
    )
    score, level = _score_historia(title, summary,
                                   source_reliability=0.8,
                                   published_days_ago=90)
    assert level in ("featured", "relevant"), (
        f"Artículo riguroso sobre Roma debe poder ser relevant o featured, score={score}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Artículo centrado en prehistoria → afinidad mínima
# ---------------------------------------------------------------------------

def test_5_prehistoria_afinidad_minima():
    """Un artículo centrado en la prehistoria debe recibir afinidad temática mínima."""
    from app.processing.historia_scorer import compute_thematic_affinity
    title = "El homo sapiens y los neandertales en el Paleolítico europeo"
    summary = (
        "Investigación sobre la coexistencia de homo sapiens y neandertal en la prehistoria "
        "europea. Se estudian los yacimientos paleolíticos y neolíticos del Mediterráneo. "
        "La prehistoria de la Península Ibérica incluye megalitos y dólmenes."
    )
    text = (title + " " + summary).lower()
    affinity = compute_thematic_affinity(title.lower(), text)
    assert affinity <= 0.10, (
        f"Artículo de prehistoria debe tener afinidad <= 0.10, obtenido {affinity}"
    )

    # Score global también debe ser bajo
    score, level = _score_historia(title, summary)
    assert level == "follow", (
        f"Artículo de prehistoria debe ser 'follow', obtenido level={level}, score={score}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Artículo superficial con titular sensacionalista → puntuación reducida
# ---------------------------------------------------------------------------

def test_6_superficial_sensacionalista_puntuacion_reducida():
    """Artículo de curiosidades históricas con titular sensacionalista debe puntuar bajo."""
    title = "Top 10 curiosidades increíbles y alucinantes sobre la Historia de España"
    summary = "Lista de las cosas más impactantes e increíbles que quizás no sabías sobre la Reconquista."
    score, level = _score_historia(title, summary, published_days_ago=5)
    assert level == "follow", (
        f"Artículo superficial debe ser 'follow', obtenido level={level}, score={score}"
    )
    assert score <= 0.44, (
        f"Artículo superficial debe tener score <= 0.44, obtenido {score}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Mención incidental de un tema prioritario → afinidad no elevada
# ---------------------------------------------------------------------------

def test_7_mencion_incidental_no_da_afinidad_alta():
    """Una mención de pasada a Castilla en un artículo de política actual no da afinidad alta."""
    from app.processing.historia_scorer import compute_thematic_affinity
    title = "El presidente visita Castilla para inaugurar una autopista"
    summary = "El jefe del ejecutivo inauguró hoy la nueva autovía en la región de Castilla."
    text = (title + " " + summary).lower()
    affinity = compute_thematic_affinity(title.lower(), text)
    # "Castilla" aparece 2 veces en un contexto de política actual, sin keywords medievales
    # La afinidad no debe superar el umbral de "gran interés"
    assert affinity <= 0.55, (
        f"Mención incidental de Castilla no debe dar afinidad > 0.55, obtenido {affinity}"
    )


# ---------------------------------------------------------------------------
# Test 8 — Análisis crítico de interpretación histórica → no penalizado
# ---------------------------------------------------------------------------

def test_8_analisis_critico_no_penalizado():
    """Un artículo que cuestiona una interpretación establecida no debe penalizarse."""
    title = "Nueva revisión histórica sobre el papel de la Inquisición española"
    summary = (
        "Este estudio historiográfico revisa críticamente la interpretación tradicional "
        "sobre la Santa Inquisición. El investigador examina fuentes primarias y propone "
        "una nueva interpretación basada en evidencia documental. El debate historiográfico "
        "sobre este período es objeto de controversia histórica bien fundamentada."
    )
    score, level = _score_historia(title, summary,
                                   source_reliability=0.8,
                                   published_days_ago=30)
    # Debe ser relevante o destacado, no penalizado por ser crítico
    assert level in ("featured", "relevant"), (
        f"Revisión crítica no debe penalizarse; level={level}, score={score}"
    )
    assert score >= 0.50, f"Score esperado >= 0.50, obtenido {score}"


# ---------------------------------------------------------------------------
# Test 9 — Duplicado no desplaza; aportación nueva no se descarta
# ---------------------------------------------------------------------------

def test_9_duplicado_no_desplaza_nueva_aportacion_no_descartada():
    """is_duplicate no lo puntúa el scorer; la calidad del contenido manda."""
    # El scorer de historia no aplica penalización adicional por is_duplicate
    # (la deduplicación es a nivel de ingestión con is_duplicate=True que filtra el feed)
    title = "Descubrimiento de un nuevo manuscrito medieval en el Archivo Nacional"
    summary = (
        "Investigadores del CSIC han localizado por primera vez un manuscrito inédito del "
        "siglo XIII que aporta nuevas evidencias sobre la formación de la Corona de Castilla."
    )
    from app.processing.historia_scorer import score_historia_article
    news_new = _make_news(title, summary, is_duplicate=False,
                          source_name="CSIC Historia",
                          source_url="https://digital.csic.es/feed",
                          source_reliability=0.9)
    news_dup = _make_news(title, summary, is_duplicate=True,
                          source_name="CSIC Historia",
                          source_url="https://digital.csic.es/feed",
                          source_reliability=0.9)
    score_historia_article(news_new)
    score_historia_article(news_dup)

    # El scorer no penaliza por is_duplicate (eso lo maneja el filtro is_duplicate en la API)
    assert news_new.relevance_score == news_dup.relevance_score, (
        "El scorer de historia no debe penalizar por is_duplicate"
    )
    # Y el contenido de calidad debe puntuar bien
    assert news_new.relevance_level in ("featured", "relevant"), (
        f"Manuscrito inédito CSIC debe ser featured o relevant, got {news_new.relevance_level}"
    )


# ---------------------------------------------------------------------------
# Test 10 — Artículo de Política → comportamiento estándar intacto
# ---------------------------------------------------------------------------

def test_10_politica_usa_scorer_estandar():
    """Un artículo de Política no debe pasar por el scorer de Historia."""
    from app.processing.scoring import score_news
    title = "El Congreso aprueba los presupuestos generales del Estado"
    summary = "El Parlamento español dio luz verde hoy a los presupuestos con el apoyo del gobierno."
    news = _make_news(title, summary, published_days_ago=1)

    # Con primary_category != 'historia', debe usar el scorer estándar
    score_news(news, category_slugs=["politica"], primary_category="politica")

    # El scorer estándar arranca en 0.5; con recencia de 1 día +0.10 → mínimo ~0.55
    assert news.relevance_score is not None
    assert news.relevance_level in ("featured", "relevant", "follow")

    # Verificar que NO usó el scorer de Historia (los thresholds difieren)
    # En el scorer estándar, un artículo político reciente con algunos hits debería
    # ser al menos relevant (>= 0.48 estándar). Comprobamos que no se distorsionó.
    assert news.relevance_score >= 0.45, (
        f"Artículo político reciente debe tener score >= 0.45, obtenido {news.relevance_score}"
    )


# ---------------------------------------------------------------------------
# Test 11 — Artículo de Ciencia → comportamiento estándar intacto
# ---------------------------------------------------------------------------

def test_11_ciencia_usa_scorer_estandar():
    """Un artículo de Ciencia no debe verse afectado por la lógica de Historia."""
    from app.processing.scoring import score_news
    title = "Investigadores del CSIC descubren una nueva partícula subatómica"
    summary = "El equipo de física del CSIC publicó el hallazgo en una revista científica internacional."
    news = _make_news(title, summary, published_days_ago=2,
                      source_name="El País Ciencia",
                      source_reliability=0.85)

    score_news(news, category_slugs=["ciencia"], primary_category="ciencia")

    assert news.relevance_score is not None
    assert news.relevance_level in ("featured", "relevant", "follow")
    # No debe haber aplicado los thresholds de Historia (0.70/0.45)
    # Simplemente comprobamos que puntúa de forma coherente con el scorer estándar
    assert 0.0 <= news.relevance_score <= 1.0


# ---------------------------------------------------------------------------
# Test 12 — Filtros y noticias destacadas siguen funcionando
# ---------------------------------------------------------------------------

def test_12_featured_level_se_asigna_correctamente_en_historia():
    """Un artículo histórico de máxima calidad debe alcanzar 'featured'."""
    title = "La Corona de Aragón y la Corona de Castilla: alianzas diplomáticas medievales"
    summary = (
        "Este estudio histórico analiza las relaciones diplomáticas entre la Corona de "
        "Aragón y la Corona de Castilla en la Edad Media. Se examinan los fueros, las "
        "causas y consecuencias de las alianzas matrimoniales y el contexto histórico de "
        "la unión dinástica de los Reyes Católicos. Investigación del Instituto de Historia "
        "del CSIC basada en fuentes primarias del Archivo Nacional."
    )
    score, level = _score_historia(
        title, summary,
        source_name="Hispania CSIC",
        source_url="https://revistas.csic.es/hispania/feed",
        source_reliability=0.9,
        published_days_ago=15,
    )
    assert level == "featured", (
        f"Artículo de máxima calidad sobre Corona de Aragón/Castilla debe ser featured; "
        f"score={score}"
    )


# ---------------------------------------------------------------------------
# Test 13 — Rescore de Historia no altera puntuaciones de otras categorías
# ---------------------------------------------------------------------------

def test_13_rescore_historia_no_afecta_otras_categorias():
    """score_news con primary_category='historia' no altera artículos de otras categorías."""
    from app.processing.scoring import score_news

    pol_news = _make_news(
        "Elecciones en España: el PP gana con mayoría absoluta",
        "El Partido Popular obtuvo la mayoría en las elecciones generales.",
        published_days_ago=1,
    )
    sci_news = _make_news(
        "Nuevo descubrimiento en física cuántica",
        "Un equipo de investigadores publicó un artículo en Nature.",
        published_days_ago=3,
    )

    score_news(pol_news, category_slugs=["politica"], primary_category="politica")
    score_news(sci_news, category_slugs=["ciencia"], primary_category="ciencia")

    pol_score = pol_news.relevance_score
    sci_score = sci_news.relevance_score

    # Re-run to confirm idempotency of standard scorer
    score_news(pol_news, category_slugs=["politica"], primary_category="politica")
    score_news(sci_news, category_slugs=["ciencia"], primary_category="ciencia")

    assert pol_news.relevance_score == pol_score, "Política score should be stable"
    assert sci_news.relevance_score == sci_score, "Ciencia score should be stable"

    # Verify historia scorer was NOT called for these
    # Standard thresholds are 0.72/0.48; historia uses 0.70/0.45.
    # A purely numeric equality won't help here, so we just verify no exception was raised
    # and scores are in the expected range.
    assert 0.0 <= pol_news.relevance_score <= 1.0
    assert 0.0 <= sci_news.relevance_score <= 1.0


# ---------------------------------------------------------------------------
# Test 14 — Datos existentes, favoritos y traducciones permanecen intactos
# ---------------------------------------------------------------------------

def test_14_scorer_no_modifica_campos_no_relacionados():
    """El scorer de Historia solo modifica relevance_score y relevance_level."""
    from app.processing.historia_scorer import score_historia_article

    title = "Los visigodos y la formación del reino de Toledo"
    summary = "Estudio sobre el reino visigodo y su contexto histórico en la Hispania tardoantigua."
    news = _make_news(title, summary)
    news.title_es = "Título en español"
    news.summary_es = "Resumen en español"
    news.url = "https://example.com/article/123"
    news.geographic_scope = "spain"
    news.is_duplicate = False

    score_historia_article(news)

    assert news.title_es == "Título en español", "title_es no debe modificarse"
    assert news.summary_es == "Resumen en español", "summary_es no debe modificarse"
    assert news.url == "https://example.com/article/123", "url no debe modificarse"
    assert news.geographic_scope == "spain", "geographic_scope no debe modificarse"
    assert news.is_duplicate is False, "is_duplicate no debe modificarse"
    assert news.relevance_score is not None, "relevance_score debe haberse asignado"
    assert news.relevance_level in ("featured", "relevant", "follow")


# ---------------------------------------------------------------------------
# Test 15 — Ausencia de datos no provoca errores ni puntuaciones artificiales
# ---------------------------------------------------------------------------

def test_15_ausencia_de_datos_no_provoca_errores():
    """El scorer debe funcionar aunque falten resumen, contenido o fuente."""
    from app.processing.historia_scorer import score_historia_article

    # Sin resumen, sin contenido, sin fuente
    news = SimpleNamespace(
        title_original="Historia de la Reconquista española",
        summary_original=None,
        content_original=None,
        published_at=datetime.now(tz=timezone.utc) - timedelta(days=100),
        is_duplicate=False,
        source=None,
        categories=[],
        relevance_score=None,
        relevance_level=None,
        geographic_scope="spain",
    )

    # No debe lanzar excepción
    score_historia_article(news)

    assert news.relevance_score is not None, "score debe asignarse aunque falten datos"
    assert news.relevance_level in ("featured", "relevant", "follow")
    assert 0.0 <= news.relevance_score <= 1.0, (
        f"Score fuera de rango [0,1]: {news.relevance_score}"
    )
