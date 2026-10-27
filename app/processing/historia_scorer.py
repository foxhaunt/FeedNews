"""Scoring personalizado para artículos de la categoría Historia.

Solo se invoca cuando 'historia' es la categoría principal del artículo.
Las demás categorías usan íntegramente el scoring estándar de scoring.py.

Dimensiones (ver WEIGHTS en historia_profile.py):
  - Afinidad temática     (40 %): coincidencia con los intereses históricos
  - Profundidad           (25 %): calidad y rigor del contenido
  - Interés historiográfico (20 %): aportación de conocimiento
  - Calidad documental    (15 %): solidez de fuentes y origen académico

Recencia: peso reducido en Historia (máx +0.05 vs +0.20 en el scorer estándar).
Un artículo excelente publicado hace meses puede superar a uno reciente mediocre.
"""
from datetime import datetime, timezone
from typing import Tuple

from app.models import News
from app.processing.historia_profile import (
    FEATURED_THRESHOLD, RELEVANT_THRESHOLD, WEIGHTS,
    PRIORITY_HIGH, PRIORITY_MEDIUM, EXCLUDED_TOPICS,
    DEPTH_SIGNALS, SUPERFICIALITY_SIGNALS, HISTORIOGRAPHIC_SIGNALS,
    QUALITY_SIGNALS, ACADEMIC_SOURCE_PATTERNS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_hits(text: str, terms: list) -> int:
    return sum(1 for t in terms if t in text)


def _term_score(text: str, title: str, terms: list,
                text_val: float, title_bonus: float, cap: int = 3) -> float:
    """Acumula puntuación por aparición de términos en texto y título.

    title_bonus se añade cuando el término aparece en el título:
    señala que el artículo ES sobre ese tema, no que lo menciona de paso.
    cap: máximo de ocurrencias por término en el texto completo.
    """
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
    """Devuelve [0.0, 1.0]. Mínimo 0.05 si el artículo trata principalmente
    de prehistoria. Floor dinámico según cobertura de temas de interés."""

    # --- Exclusión por prehistoria ---
    excl_title = any(t in title for t in EXCLUDED_TOPICS)
    excl_text = _count_hits(text, EXCLUDED_TOPICS)
    if excl_title or excl_text >= 2:
        return 0.05

    # --- Puntuación por temas prioritarios ---
    high = _term_score(text, title, PRIORITY_HIGH,
                       text_val=0.07, title_bonus=0.18, cap=3)
    med  = _term_score(text, title, PRIORITY_MEDIUM,
                       text_val=0.04, title_bonus=0.10, cap=2)

    high = min(high, 0.85)
    med  = min(med, 0.60)

    score = high + med * 0.30

    # Floor dinámico según cobertura de temas de interés medio
    if med >= 0.35:
        score = max(score, 0.50)
    elif med >= 0.15:
        score = max(score, 0.42)
    else:
        score = max(score, 0.32)

    # Si hay una mención de prehistoria (sin dominar), se limita el techo
    if excl_text == 1:
        score = min(score, 0.45)
        score = max(score, 0.25)

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Dimensión 2 — Profundidad del contenido
# ---------------------------------------------------------------------------

def compute_depth(text: str, summary: str) -> float:
    """Devuelve [0.0, 1.0]. Penaliza sensacionalismo; bonifica señales de rigor."""
    score = 0.30  # baseline

    # Longitud del resumen como proxy (necesaria pero no suficiente)
    slen = len(summary) if summary else 0
    if slen > 400:
        score += 0.20
    elif slen > 200:
        score += 0.12
    elif slen > 80:
        score += 0.06

    # Señales de profundidad
    depth_hits = _count_hits(text, DEPTH_SIGNALS)
    score += min(depth_hits * 0.08, 0.40)

    # Penalización por superficialidad / sensacionalismo
    superf_hits = _count_hits(text, SUPERFICIALITY_SIGNALS)
    score -= superf_hits * 0.12

    return max(0.0, min(score, 1.0))


# ---------------------------------------------------------------------------
# Dimensión 3 — Interés historiográfico
# ---------------------------------------------------------------------------

def compute_historiographic(text: str, source_name: str = "") -> float:
    """Devuelve [0.0, 1.0]. Valora aportación de conocimiento y origen académico."""
    score = 0.30  # baseline

    hits = _count_hits(text, HISTORIOGRAPHIC_SIGNALS)
    score += min(hits * 0.12, 0.48)

    # Bonus por nombre de fuente académica
    src_lower = source_name.lower()
    if any(p in src_lower for p in ["csic", "ucm", "uned", "universidad", "revista", "journal"]):
        score += 0.20

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Dimensión 4 — Calidad documental
# ---------------------------------------------------------------------------

def compute_documentary_quality(text: str, source) -> float:
    """Devuelve [0.0, 1.0]. Combina fiabilidad de fuente y señales en texto."""
    reliability = 0.65
    if source is not None:
        reliability = getattr(source, "reliability_score", 0.65) or 0.65

    score = reliability  # rango típico [0.45, 0.95]

    # Señales de calidad en el texto
    quality_hits = _count_hits(text, QUALITY_SIGNALS)
    score += min(quality_hits * 0.08, 0.24)

    # Bonus por URL académica
    if source is not None:
        src_url = (getattr(source, "url", "") or "").lower()
        if any(p in src_url for p in ACADEMIC_SOURCE_PATTERNS):
            score += 0.10

    return max(0.0, min(score, 1.0))


# ---------------------------------------------------------------------------
# Recencia — peso reducido
# ---------------------------------------------------------------------------

def _recency_bonus(published_at) -> float:
    """Bonificación por recencia, máx +0.05 (vs +0.20 del scorer estándar).
    Un artículo histórico excelente de hace meses debe superar a uno reciente mediocre."""
    if published_at is None:
        return 0.0
    now = datetime.now(tz=timezone.utc)
    pub = published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    age_hours = (now - pub).total_seconds() / 3600
    if age_hours < 24:
        return 0.05
    if age_hours < 24 * 90:   # < 3 meses
        return 0.02
    return 0.0


# ---------------------------------------------------------------------------
# Función pública
# ---------------------------------------------------------------------------

def score_historia_article(news: News) -> Tuple[float, str]:
    """Puntúa un artículo cuya categoría principal es Historia.

    Returns:
        (relevance_score, relevance_level)

    Solo debe llamarse cuando 'historia' es la categoría principal.
    Modifica news.relevance_score y news.relevance_level IN PLACE además
    de devolver los valores, para coincidir con la interfaz de score_news().
    """
    title   = (news.title_original or "").lower().strip()
    summary = news.summary_original or ""
    content = news.content_original or ""
    # Texto de búsqueda: título + resumen + primeros 600 chars del cuerpo
    text = (title + " " + summary.lower() + " " + content[:600].lower()).strip()

    source = getattr(news, "source", None)
    source_name = (getattr(source, "name", "") or "") if source else ""

    w = WEIGHTS
    score = (
        w["thematic_affinity"]   * compute_thematic_affinity(title, text)
        + w["content_depth"]     * compute_depth(text, summary)
        + w["historiographic"]   * compute_historiographic(text, source_name)
        + w["documentary_quality"] * compute_documentary_quality(text, source)
    )

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
