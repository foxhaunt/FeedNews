from datetime import datetime, timezone
from app.models import News

# Tier-1: rare high-impact events — each hit adds a larger bonus
_TIER1_KEYWORDS = [
    "guerra", "war", "atentado", "terrorist attack", "golpe de estado", "coup",
    "declaración de guerra", "state of emergency", "estado de emergencia",
    "bomba", "bomb", "ataque", "attack", "misil", "missile",
    "muertos", "killed", "dead", "víctimas", "victims",
    "terremoto", "earthquake", "tsunami", "huracán", "hurricane",
    "explosión", "explosion", "accidente grave", "catastrophe",
]

# Tier-2: common newsworthy terms — each hit adds a smaller bonus
_TIER2_KEYWORDS = [
    "elecciones", "election", "referéndum", "referendum",
    "dimisión", "resign", "detenido", "arrested",
    "crisis", "emergencia", "emergency",
    "sanciones", "sanctions", "acuerdo", "agreement", "tratado", "treaty",
    "banco central", "central bank", "tipos de interés", "interest rate",
    "otan", "nato", "onu", "united nations",
    "tribunal supremo", "supreme court", "condena", "sentence",
]

CATEGORY_WEIGHTS = {
    "defensa": 1.25,
    "geopolitica": 1.2,
    "politica": 1.1,
    "economia": 1.1,
    "seguridad": 1.08,
    "sucesos": 1.08,
    "energia": 1.05,
    "ciencia": 1.0,
    "tecnologia": 1.0,
    "sociedad": 0.95,
}

GEO_WEIGHTS = {
    "spain": 1.05,
    "europe": 1.02,
    "international": 1.0,
}


def score_news(news: News, category_slugs: list = None, primary_category: str = None):
    """Compute a relevance score [0..1] and set relevance_level.

    When primary_category == 'historia' (or category_slugs[0] == 'historia'),
    delegates to historia_scorer.score_historia_article() which applies a
    personalized scoring profile. All other categories use the standard formula.

    Standard design:
    - base 0.5 (neutral starting point)
    - recency bonus up to +0.2
    - keyword bonus: tier-1 (rare events) +0.08/hit max 0.2; tier-2 (common) +0.03/hit max 0.09
    - category and geo multipliers are small (≤1.25) to avoid domination
    - source reliability acts as a ±20% soft adjustment, not a full multiplier,
      so lower-reliability sources aren't unfairly suppressed
    """
    # Determine primary category if not provided
    if primary_category is None and category_slugs:
        primary_category = category_slugs[0]
    if primary_category is None and news.categories:
        primary_category = news.categories[0].slug

    # Personalized scoring for Historia
    if primary_category == "historia":
        from app.processing.historia_scorer import score_historia_article
        score_historia_article(news)
        return

    score = 0.5

    # Recency bonus (max 0.2)
    now = datetime.now(tz=timezone.utc)
    pub = news.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    age_hours = (now - pub).total_seconds() / 3600
    if age_hours < 1:
        score += 0.2
    elif age_hours < 6:
        score += 0.15
    elif age_hours < 24:
        score += 0.1
    elif age_hours < 72:
        score += 0.05

    # Keyword bonus — tier-1 and tier-2 kept separate
    text = (news.title_original or "").lower() + " " + (news.summary_original or "").lower()
    t1_hits = sum(1 for kw in _TIER1_KEYWORDS if kw in text)
    t2_hits = sum(1 for kw in _TIER2_KEYWORDS if kw in text)
    score += min(t1_hits * 0.08, 0.20)
    score += min(t2_hits * 0.03, 0.09)

    # Category multiplier
    if category_slugs is None:
        category_slugs = [c.slug for c in (news.categories or [])]
    cat_mult = max((CATEGORY_WEIGHTS.get(s, 1.0) for s in category_slugs), default=1.0)
    score *= cat_mult

    # Geographic scope multiplier
    score *= GEO_WEIGHTS.get(news.geographic_scope, 1.0)

    # Source reliability: soft ±20% adjustment around neutral 0.7
    # A 0.9-reliability source adds ~+5.7%; a 0.45-reliability source subtracts ~-17.5%
    # This avoids fully suppressing low-reliability sources while still rewarding
    # established ones.
    if news.source:
        rel = news.source.reliability_score
        reliability_adj = 1.0 + (rel - 0.7) * 0.5   # range ~[0.875, 1.1] for rel in [0.45, 0.95]
        score *= reliability_adj

    score = max(0.0, min(1.0, score))
    news.relevance_score = round(score, 4)

    if score >= 0.72:
        news.relevance_level = "featured"
    elif score >= 0.48:
        news.relevance_level = "relevant"
    else:
        news.relevance_level = "follow"
