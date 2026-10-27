"""Scoring personalizado para artículos de la categoría Catolicismo y Tradicionalismo.

Solo se invoca cuando 'catolicismo' es la categoría principal del artículo.
Las demás categorías usan íntegramente el scoring estándar de scoring.py.

Dimensiones (ver WEIGHTS en catolicismo_profile.py):
  - Afinidad temática     (40 %): liturgia tradicional, tomismo, doctrina
  - Profundidad doctrinal (25 %): rigor teológico vs sensacionalismo
  - Contexto eclesial     (20 %): enraizamiento en tradición y magisterio
  - Calidad de fuente     (15 %): solidez de los medios y fiabilidad

Recencia: peso reducido (máx +0.05). Un artículo teológico serio de hace
meses puede superar a una noticia superficial de hoy.
"""
from datetime import datetime, timezone
from typing import Tuple

from app.models import News
from app.processing.catolicismo_profile import (
    FEATURED_THRESHOLD, RELEVANT_THRESHOLD, WEIGHTS,
    PRIORITY_HIGH, PRIORITY_MEDIUM,
    DEPTH_SIGNALS, SUPERFICIALITY_SIGNALS, ECCLESIAL_CONTEXT_SIGNALS,
    QUALITY_SIGNALS, TRUSTED_SOURCE_PATTERNS,
    TRADITIONALIST_EDITORIAL, TRADITIONALIST_AFFINITY_BONUS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_hits(text: str, terms: list) -> int:
    return sum(1 for t in terms if t in text)


def _has_high_priority_content(title: str, text: str) -> bool:
    """Returns True if any PRIORITY_HIGH term appears anywhere in the article."""
    return _term_score(text, title, PRIORITY_HIGH,
                       text_val=1.0, title_bonus=0, cap=1) > 0


def _term_score(text: str, title: str, terms: list,
                text_val: float, title_bonus: float, cap: int = 3) -> float:
    score = 0.0
    for t in terms:
        occ = min(text.count(t), cap)
        score += occ * text_val
        if t in title:
            score += title_bonus
    return score


# ---------------------------------------------------------------------------
# Dimensión 1 — Afinidad temática
# ---------------------------------------------------------------------------

def compute_thematic_affinity(title: str, text: str) -> float:
    """Devuelve [0.0, 1.0]. Combina temas de alta y media prioridad."""
    high = _term_score(text, title, PRIORITY_HIGH,
                       text_val=0.07, title_bonus=0.18, cap=3)
    med  = _term_score(text, title, PRIORITY_MEDIUM,
                       text_val=0.04, title_bonus=0.10, cap=2)

    high = min(high, 0.85)
    med  = min(med,  0.60)

    score = high + med * 0.30

    # Floor dinámico: garantiza una puntuación mínima de interés cuando hay
    # cobertura de temas de media prioridad.
    #
    # Los suelos son moderados para que los artículos genéricos (p. ej. solo
    # "papa" + "cardenal") no alcancen el mismo nivel que los que tocan temas
    # de alta prioridad (liturgia tradicional, tomismo, magisterio). El rango
    # real de la afinidad temática queda libre para diferenciar.
    if med >= 0.35:
        score = max(score, 0.38)   # era 0.50 — evita empatar con artículos con HIGH hits
    elif med >= 0.15:
        score = max(score, 0.28)   # era 0.42
    else:
        score = max(score, 0.18)   # era 0.32

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Dimensión 2 — Profundidad doctrinal
# ---------------------------------------------------------------------------

def compute_doctrinal_depth(text: str, summary: str) -> float:
    """Devuelve [0.0, 1.0]. Penaliza sensacionalismo; bonifica rigor teológico."""
    score = 0.30  # baseline

    slen = len(summary) if summary else 0
    if slen > 400:
        score += 0.20
    elif slen > 200:
        score += 0.12
    elif slen > 80:
        score += 0.06

    depth_hits = _count_hits(text, DEPTH_SIGNALS)
    score += min(depth_hits * 0.08, 0.40)

    superf_hits = _count_hits(text, SUPERFICIALITY_SIGNALS)
    score -= superf_hits * 0.12

    return max(0.0, min(score, 1.0))


# ---------------------------------------------------------------------------
# Dimensión 3 — Contexto eclesial
# ---------------------------------------------------------------------------

def compute_ecclesial_context(text: str, source_name: str = "") -> float:
    """Devuelve [0.0, 1.0]. Valora enraizamiento en tradición y magisterio.

    El bono se basa exclusivamente en el contenido del artículo (señales
    eclesiales en el texto).  El nombre de la fuente no influye: hacerlo
    favorecía mecánicamente a fuentes institucionales de alto volumen.
    """
    score = 0.30  # baseline

    hits = _count_hits(text, ECCLESIAL_CONTEXT_SIGNALS)
    score += min(hits * 0.12, 0.48)

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Dimensión 4 — Calidad de fuente
# ---------------------------------------------------------------------------

def compute_source_quality(text: str, source) -> float:
    """Devuelve [0.0, 1.0]. Combina fiabilidad de fuente y señales en texto."""
    reliability = 0.65
    if source is not None:
        reliability = getattr(source, "reliability_score", 0.65) or 0.65

    score = reliability

    quality_hits = _count_hits(text, QUALITY_SIGNALS)
    score += min(quality_hits * 0.08, 0.24)

    if source is not None:
        src_url = (getattr(source, "url", "") or "").lower()
        if any(p in src_url for p in TRUSTED_SOURCE_PATTERNS):
            score += 0.10

    return max(0.0, min(score, 1.0))


# ---------------------------------------------------------------------------
# Recencia — peso reducido
# ---------------------------------------------------------------------------

def _recency_bonus(published_at) -> float:
    """Bonificación por recencia, máx +0.05 (vs +0.20 del scorer estándar)."""
    if published_at is None:
        return 0.0
    now = datetime.now(tz=timezone.utc)
    pub = published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    age_hours = (now - pub).total_seconds() / 3600
    if age_hours < 24:
        return 0.05
    if age_hours < 24 * 90:
        return 0.02
    return 0.0


# ---------------------------------------------------------------------------
# Función pública
# ---------------------------------------------------------------------------

def score_catolicismo_article(news: News) -> Tuple[float, str]:
    """Puntúa un artículo cuya categoría principal es Catolicismo.

    Returns:
        (relevance_score, relevance_level)

    Solo debe llamarse cuando 'catolicismo' es la categoría principal.
    Modifica news.relevance_score y news.relevance_level IN PLACE.
    """
    title   = (news.title_original or "").lower().strip()
    summary = news.summary_original or ""
    content = news.content_original or ""
    text = (title + " " + summary.lower() + " " + content[:600].lower()).strip()

    source      = getattr(news, "source", None)
    source_name = (getattr(source, "name", "") or "") if source else ""

    # Determine editorial type (set in extra_config by seeds.py)
    editorial = None
    if source is not None:
        extra = getattr(source, "extra_config", None) or {}
        editorial = extra.get("editorial") if isinstance(extra, dict) else None

    w = WEIGHTS
    thematic = compute_thematic_affinity(title, text)
    score = (
        w["thematic_affinity"] * thematic
        + w["doctrinal_depth"]  * compute_doctrinal_depth(text, summary)
        + w["ecclesial_context"] * compute_ecclesial_context(text, source_name)
        + w["source_quality"]   * compute_source_quality(text, source)
    )

    # Traditionalist sources with pertinent content get a priority boost.
    # Fires when the source is explicitly traditionalist AND the article
    # contains at least one PRIORITY_HIGH term OR a strong ecclesial context
    # signal (≥ 1 hit → compute_ecclesial_context ≥ 0.42).
    # This avoids promoting generic institutional news from traditionalist
    # sources (papal schedules, cardinal appointments) while still rewarding
    # doctrinal and liturgical articles regardless of floor-driven thematic score.
    if editorial == TRADITIONALIST_EDITORIAL and (
        _has_high_priority_content(title, text)
        or compute_ecclesial_context(text) >= 0.42
    ):
        score += TRADITIONALIST_AFFINITY_BONUS

    score += _recency_bonus(news.published_at)
    score = round(max(0.0, min(1.0, score)), 4)

    if score >= FEATURED_THRESHOLD:
        level = "featured"
    elif score >= RELEVANT_THRESHOLD:
        level = "relevant"
    else:
        level = "follow"

    news.relevance_score = score
    news.relevance_level = level
    return score, level
