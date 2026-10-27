"""
Keyword-based news categorizer.

Each category has a list of (keyword, weight) pairs.  A keyword is
matched with word-boundary regex (`\b`) so that "un" does not match
every Spanish "un…" word, "ai" does not match "air", "data" does not
match "update", etc.  Multi-word phrases use substring matching (no
`\b` needed since word-boundaries are enforced by the spaces).

Scoring:
  - Weight 2 = high-confidence keyword (one match is sufficient)
  - Weight 1 = general keyword (two matches needed to reach threshold)
  - threshold (default 2) = minimum total score to assign the category

Assignment rules:
  1. Compute score for every category.
  2. Assign primary category = highest score (score ≥ threshold).
  3. Assign secondary categories = all others with score ≥ threshold,
     up to 2 additional categories.
  4. Total categories: max 3 (primary + up to 2 secondary).
  5. If no category reaches threshold → return [] (article gets no tags).
     Do NOT default to "sociedad".
"""
import re
import logging
from typing import List, Optional, Tuple
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import News, Category, news_categories

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword definitions
# Format per entry:
#   (slug,
#    [(kw_es, weight), ...],   # Spanish keywords
#    [(kw_en, weight), ...],   # English keywords
#    threshold)                # minimum score to assign this category
# ---------------------------------------------------------------------------

_CATEGORIES: List[Tuple] = [

    # ── Historia ────────────────────────────────────────────────────────────
    # History, archaeology, heritage. Threshold=2 so "historia" in a headline
    # about something else (e.g. "hará historia este partido") does not fire.
    ("historia",
     [
         ("historia medieval", 2), ("historia moderna", 2),
         ("historia contemporánea", 2), ("historia antigua", 2),
         ("edad media", 2), ("edad moderna", 2), ("reconquista", 2),
         ("arqueología", 2), ("patrimonio histórico", 2),
         ("patrimonio cultural", 2), ("yacimiento", 2), ("excavación", 2),
         ("civilización", 2), ("imperio romano", 2), ("antigüedad", 2),
         ("prehistoria", 2), ("neolítico", 2), ("bronce", 1),
         ("renacimiento", 2), ("ilustración histórica", 2),
         ("revolución francesa", 2), ("primera guerra mundial", 2),
         ("segunda guerra mundial", 2), ("franquismo", 2),
         ("transición española", 2), ("siglo xix", 2), ("siglo xx", 2),
         ("siglo xvi", 2), ("siglo xvii", 2), ("siglo xviii", 2),
         ("monarquía española", 2), ("corona española", 2),
         ("inquisición", 2), ("conquista americana", 2),
         ("historiador", 2), ("fuentes históricas", 2),
     ],
     [
         ("medieval history", 2), ("ancient history", 2),
         ("middle ages", 2), ("renaissance", 2), ("archaeology", 2),
         ("historical heritage", 2), ("cultural heritage", 2),
         ("excavation site", 2), ("civilization", 2),
         ("roman empire", 2), ("antiquity", 2), ("prehistory", 2),
         ("french revolution", 2), ("world war i", 2), ("world war ii", 2),
         ("cold war history", 2), ("historical research", 2),
         ("historian", 2), ("historical sources", 2),
         ("16th century", 2), ("17th century", 2), ("18th century", 2),
         ("19th century", 2), ("20th century history", 2),
         ("spanish inquisition", 2), ("age of discovery", 2),
     ],
     2),

    # ── Política ────────────────────────────────────────────────────────────
    # Elections, parties, legislatures, government decisions.
    # Does NOT fire just because a politician is mentioned in another context.
    ("politica",
     [
         ("elecciones", 2), ("votación", 2), ("referéndum", 2),
         ("campaña electoral", 2), ("partido político", 2),
         ("congreso de los diputados", 2), ("parlamento", 1),
         ("senado español", 2), ("senado", 1), ("legislativo", 1),
         ("legislatura", 1), ("diputado", 1), ("coalición", 1),
         ("oposición política", 2), ("oposición", 1), ("primera ministra", 2),
         ("primer ministro", 2), ("presidente del gobierno", 2),
         ("democracia", 1), ("voto", 1), ("urnas", 2),
     ],
     [
         ("election", 2), ("vote", 1), ("ballot", 2), ("referendum", 2),
         ("parliament", 1), ("congress", 1), ("senate", 1),
         ("political party", 2), ("prime minister", 2), ("democracy", 1),
         ("legislation", 1), ("opposition party", 2), ("coalition", 1),
         ("presidential race", 2), ("runoff", 2), ("gubernatorial", 2),
         ("lawmaker", 2), ("legislator", 2),
     ],
     2),

    # ── Economía y mercados ─────────────────────────────────────────────────
    ("economia",
     [
         ("economía", 2), ("mercado financiero", 2), ("bolsa de valores", 2),
         ("bolsa", 1), ("inflación", 2), ("pib", 2), ("banco central", 2),
         ("deuda pública", 2), ("déficit", 2), ("recesión", 2),
         ("desempleo", 2), ("paro", 1), ("exportación", 1),
         ("importación", 1), ("euribor", 2), ("tipo de interés", 2),
         ("impuesto", 1), ("fiscal", 1), ("presupuesto", 1),
         ("crecimiento económico", 2), ("banco", 1), ("inversión", 1),
         ("divisa", 2), ("prima de riesgo", 2), ("opep", 2),
         ("política fiscal", 2), ("consolidación fiscal", 2),
         ("paraíso fiscal", 2), ("impuestos", 1),
     ],
     [
         ("economy", 2), ("stock market", 2), ("stock exchange", 2),
         ("inflation", 2), ("gdp", 2), ("central bank", 2), ("debt", 1),
         ("deficit", 2), ("recession", 2), ("unemployment", 2),
         ("interest rate", 2), ("tax", 1), ("budget", 1), ("fiscal policy", 2),
         ("tax haven", 2),
         ("bond market", 2), ("treasury", 1), ("trade balance", 2),
         ("investment", 1), ("opec", 2), ("monetary policy", 2),
         ("fed", 1), ("ecb", 2), ("imf", 2), ("world bank", 2),
     ],
     2),

    # ── Geopolítica ─────────────────────────────────────────────────────────
    # International relations, diplomacy, strategic rivalries.
    # NOT triggered merely because a foreign country is mentioned.
    ("geopolitica",
     [
         ("relaciones internacionales", 2), ("relaciones exteriores", 2),
         ("diplomacia", 2), ("diplomático", 2), ("política exterior", 2),
         ("tratado internacional", 2), ("acuerdo internacional", 2),
         ("sanciones internacionales", 2), ("cumbre diplomática", 2),
         ("embajador", 2), ("embajada", 1), ("onu", 2),
         ("naciones unidas", 2), ("g7", 2), ("g20", 2), ("brics", 2),
         ("alianza estratégica", 2), ("otan", 1), ("tensión diplomática", 2),
         ("negociación de paz", 2), ("rivalidad geopolítica", 2),
         ("negociaciones diplomáticas", 2), ("acuerdos internacionales", 2),
         ("negociaciones internacionales", 2),
     ],
     [
         ("international relations", 2), ("diplomacy", 2), ("diplomatic", 2),
         ("foreign policy", 2), ("treaty", 2), ("international agreement", 2),
         ("international agreements", 2), ("diplomatic negotiations", 2),
         ("sanctions", 2), ("diplomatic summit", 2), ("ambassador", 2),
         ("united nations", 2), ("g7", 2), ("g20", 2), ("brics", 2),
         ("strategic alliance", 2), ("nato summit", 2), ("geopolitics", 2),
         ("geopolitical", 2), ("peace talks", 2), ("state visit", 2),
         ("foreign minister", 2), ("bilateral talks", 2),
     ],
     2),

    # ── Defensa y conflictos ────────────────────────────────────────────────
    # Wars, military operations, armed forces, combat.
    # NOT triggered by police incidents, accidents or lone "attack" mentions.
    ("defensa",
     [
         ("guerra", 2), ("conflicto armado", 2), ("operación militar", 2),
         ("ejército", 2), ("fuerzas armadas", 2), ("fuerza aérea", 2),
         ("misil", 2), ("misiles", 2), ("bombardeo", 2), ("soldado", 2),
         ("tropas", 2), ("ofensiva militar", 2), ("combate", 2),
         ("artillería", 2), ("tanque", 2), ("portaaviones", 2),
         ("ataque aéreo", 2), ("alto el fuego", 2), ("cese al fuego", 2),
         ("armamento", 2), ("muertos en combate", 2),
         ("guardia nacional", 2), ("infantería", 2), ("marina militar", 2),
     ],
     [
         ("war", 2), ("armed conflict", 2), ("military operation", 2),
         ("armed forces", 2), ("air force", 2), ("navy", 2),
         ("missile strike", 2), ("airstrike", 2), ("bombing", 2),
         ("soldiers", 2), ("troops", 2), ("military offensive", 2),
         ("combat", 2), ("artillery", 2), ("armored", 2),
         ("ceasefire", 2), ("warplane", 2), ("warship", 2),
         ("battlefield", 2), ("front line", 2), ("tank", 2),
         ("infantry", 2), ("nato forces", 2),
     ],
     2),

    # ── Seguridad ───────────────────────────────────────────────────────────
    # Cybersecurity, terrorism, espionage, threats to public/national security.
    ("seguridad",
     [
         ("ciberseguridad", 2), ("ciberataque", 2), ("hackeo", 2),
         ("ransomware", 2), ("malware", 2), ("vulnerabilidad informática", 2),
         ("brecha de seguridad", 2), ("ataque informático", 2),
         ("terrorismo", 2), ("atentado terrorista", 2), ("célula terrorista", 2),
         ("espionaje", 2), ("contrainteligencia", 2), ("cni", 2),
         ("europol", 2), ("interpol", 2), ("amenaza cibernética", 2),
         ("phishing", 2), ("ciberespionaje", 2), ("yihadista", 2),
         ("yihadismo", 2), ("daesh", 2), ("al qaeda", 2),
     ],
     [
         ("cybersecurity", 2), ("cyberattack", 2), ("cyber attack", 2),
         ("hacking", 2), ("ransomware", 2), ("malware", 2),
         ("data breach", 2), ("security vulnerability", 2),
         ("terrorism", 2), ("terrorist attack", 2), ("jihadist", 2),
         ("espionage", 2), ("intelligence agency", 2),
         ("cia", 2), ("fbi", 2), ("mi6", 2), ("mossad", 2),
         ("counterterrorism", 2), ("surveillance program", 2),
         ("phishing", 2), ("zero-day", 2),
     ],
     2),

    # ── Tecnología e IA ─────────────────────────────────────────────────────
    # AI, software, hardware, tech companies, digital innovation.
    # NOT triggered by single mentions of data, digital, or tech.
    ("tecnologia",
     [
         ("inteligencia artificial", 2), ("aprendizaje automático", 2),
         ("chatgpt", 2), ("modelo de lenguaje", 2), ("robot", 1),
         ("semiconductores", 2), ("chip", 1), ("software", 1),
         ("startup tecnológica", 2), ("aplicación móvil", 2),
         ("criptomoneda", 2), ("blockchain", 2), ("5g", 2),
         ("internet de las cosas", 2), ("computación cuántica", 2),
         ("openai", 2), ("tesla", 1), ("spacex", 2),
         ("telecomunicaciones", 1), ("red neuronal", 2), ("algoritmo", 1),
         ("plataforma digital", 1), ("cibernética", 1),
     ],
     [
         ("artificial intelligence", 2), ("machine learning", 2),
         ("chatgpt", 2), ("large language model", 2), ("semiconductor", 2),
         ("chip manufacturer", 2), ("software", 1), ("hardware", 1),
         ("tech company", 2), ("smartphone", 2), ("cryptocurrency", 2),
         ("blockchain", 2), ("5g network", 2), ("quantum computing", 2),
         ("openai", 2), ("silicon valley", 2), ("app store", 2),
         ("cybernetics", 1), ("neural network", 2), ("algorithm", 1),
         ("cloud computing", 2), ("data center", 2), ("autonomous vehicle", 2),
         ("drone technology", 2), ("space technology", 2),
     ],
     2),

    # ── Ciencia y salud ─────────────────────────────────────────────────────
    ("ciencia",
     [
         ("investigación científica", 2), ("estudio científico", 2),
         ("descubrimiento científico", 2), ("ensayo clínico", 2),
         ("vacuna", 2), ("pandemia", 2), ("tratamiento médico", 2),
         ("fármaco", 2), ("antibiótico", 2), ("cáncer", 2),
         ("enfermedad", 1), ("salud pública", 2), ("hospital", 1),
         ("medicina", 2), ("virus", 1), ("genética", 2),
         ("nasa", 2), ("agencia espacial", 2), ("planeta", 1),
         ("fósil", 2), ("biología", 2), ("neurociencia", 2),
         ("epidemia", 2), ("brote", 1), ("covid", 2),
     ],
     [
         ("scientific research", 2), ("medical study", 2),
         ("scientific discovery", 2), ("clinical trial", 2),
         ("vaccine", 2), ("pandemic", 2), ("medical treatment", 2),
         ("drug approval", 2), ("antibiotic", 2), ("cancer", 2),
         ("disease", 1), ("public health", 2), ("hospital", 1),
         ("medicine", 1), ("virus", 1), ("genetics", 2),
         ("nasa", 2), ("space agency", 2), ("planet", 1),
         ("fossil", 2), ("biology", 2), ("neuroscience", 2),
         ("epidemic", 2), ("outbreak", 2), ("genome", 2),
     ],
     2),

    # ── Sociedad y tribunales ───────────────────────────────────────────────
    # Courts, judicial proceedings, social issues.
    # NOT triggered merely because people are affected.
    ("sociedad",
     [
         ("tribunal", 2), ("sentencia", 2), ("juicio oral", 2),
         ("condena penal", 2), ("absolución", 2), ("juez", 1),
         ("fiscalía", 2), ("corrupción", 1), ("tribunal supremo", 2),
         ("audiencia nacional", 2), ("derechos humanos", 2),
         ("igualdad de género", 2), ("discriminación", 2),
         ("migrantes", 1), ("crisis migratoria", 2), ("asilo", 1),
         ("vivienda", 1), ("desahucios", 2), ("educación", 1),
         ("violencia de género", 2), ("feminismo", 2),
     ],
     [
         ("court ruling", 2), ("verdict", 2), ("criminal trial", 2),
         ("prison sentence", 2), ("acquittal", 2), ("judge", 1),
         ("prosecutor", 1), ("corruption case", 2), ("supreme court", 2),
         ("human rights", 2), ("gender equality", 2), ("discrimination", 2),
         ("migration crisis", 2), ("asylum seeker", 2),
         ("housing crisis", 2), ("education policy", 2),
         ("domestic violence", 2), ("feminism", 2),
     ],
     2),

    # ── Energía y medioambiente ─────────────────────────────────────────────
    ("energia",
     [
         ("cambio climático", 2), ("calentamiento global", 2),
         ("energía renovable", 2), ("energía solar", 2),
         ("energía eólica", 2), ("energía nuclear", 2),
         ("petróleo", 2), ("gas natural", 2), ("opep", 2),
         ("emisiones de co2", 2), ("huella de carbono", 2),
         ("contaminación", 1), ("medioambiente", 2), ("biodiversidad", 2),
         ("transición energética", 2), ("panel solar", 2),
         ("hidrógeno verde", 2), ("acuerdo de París", 2), ("cop", 1),
         ("combustible fósil", 2), ("derrame de petróleo", 2),
     ],
     [
         ("climate change", 2), ("global warming", 2),
         ("renewable energy", 2), ("solar energy", 2),
         ("wind energy", 2), ("nuclear power", 2),
         ("oil price", 2), ("natural gas", 2), ("opec", 2),
         ("carbon emissions", 2), ("carbon footprint", 2),
         ("pollution", 1), ("environment", 1), ("biodiversity", 2),
         ("energy transition", 2), ("solar panel", 2),
         ("green hydrogen", 2), ("paris agreement", 2),
         ("fossil fuel", 2), ("oil spill", 2),
     ],
     2),

    # ── Sucesos y emergencias ───────────────────────────────────────────────
    # Accidents, natural disasters, fires, rescues.
    # Very specific keywords; threshold=1 so ONE strong keyword is enough.
    ("sucesos",
     [
         ("terremoto", 2), ("inundación", 2), ("incendio forestal", 2),
         ("incendio", 1), ("accidente de tráfico", 2),
         ("accidente de avión", 2), ("accidente ferroviario", 2),
         ("emergencia", 1), ("catástrofe", 2), ("tsunami", 2),
         ("huracán", 2), ("tornado", 2), ("tifón", 2),
         ("explosión", 1), ("derrumbe", 2), ("avalancha", 2),
         ("naufragio", 2), ("rescatistas", 2), ("evacuación de emergencia", 2),
         ("víctimas mortales", 2), ("fallecidos", 1), ("heridos", 1),
         ("búsqueda y rescate", 2), ("nivel de alerta", 2),
     ],
     [
         ("earthquake", 2), ("flood", 2), ("wildfire", 2),
         ("forest fire", 2), ("traffic accident", 2), ("plane crash", 2),
         ("train crash", 2), ("emergency", 1), ("disaster", 2),
         ("tsunami", 2), ("hurricane", 2), ("tornado", 2), ("typhoon", 2),
         ("explosion", 1), ("building collapse", 2), ("avalanche", 2),
         ("shipwreck", 2), ("rescue operation", 2),
         ("emergency evacuation", 2), ("casualties", 1),
         ("fatalities", 1), ("missing persons", 2),
     ],
     1),  # threshold=1: one strong keyword (terremoto, huracán...) is enough
]


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _word_in(kw: str, text: str) -> bool:
    """True if keyword appears as a complete word/phrase in text."""
    if " " in kw:
        # Multi-word phrase: simple substring check (case-insensitive)
        return kw.lower() in text
    # Single word: word-boundary regex prevents substring over-matching
    return bool(re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text, re.IGNORECASE))


def score_category(text: str, kw_es: list, kw_en: list) -> int:
    """Return total weight score for this category against the given text.

    Keywords identical across ES and EN lists (e.g. 'ransomware', 'fiscal')
    are deduplicated so they only count once, preventing a single word from
    reaching the threshold by accident via double-counting.
    """
    # Merge: keep max weight for any keyword that appears in both lists
    merged: dict[str, int] = {}
    for kw, weight in kw_es + kw_en:
        key = kw.lower()
        if key not in merged or weight > merged[key]:
            merged[key] = weight
    return sum(w for kw, w in merged.items() if _word_in(kw, text))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_text(title: str, summary: str) -> List[str]:
    """
    Return a list of category slugs for the article (primary first).

    At most 3 categories are returned (1 primary + up to 2 secondary).
    Returns [] if no category reaches its threshold.
    """
    text = ((title or "") + " " + (summary or "")).lower().strip()
    if not text:
        return []

    scored: List[Tuple[str, int]] = []
    for slug, kw_es, kw_en, threshold in _CATEGORIES:
        score = score_category(text, kw_es, kw_en)
        if score >= threshold:
            scored.append((slug, score))

    if not scored:
        return []

    # Sort by score descending, keep primary first
    scored.sort(key=lambda x: -x[1])

    # Max 3 categories
    return [slug for slug, _ in scored[:3]]


def _passes_secondary_threshold(slug: str, text: str) -> bool:
    """True if ``slug``'s score on ``text`` reaches twice its normal threshold.

    Used to filter secondary categories when a source has a forced primary
    category: prevents a single general keyword (e.g. "guerra", "diplomacia")
    from firing a category by coincidence when the article is about a
    historical *topic* rather than a current event.
    """
    entry = next((e for e in _CATEGORIES if e[0] == slug), None)
    if entry is None:
        return False
    _, kw_es, kw_en, threshold = entry
    return score_category(text, kw_es, kw_en) >= threshold * 2


async def categorize_news(
    news: News,
    session: AsyncSession,
    source_primary_category: Optional[str] = None,
) -> List[str]:
    """Assign categories to a news item and persist them.

    source_primary_category: if set (e.g. 'historia'), it is forced as the
    primary slug regardless of keyword scores.  Secondary categories are kept
    only when their score is ≥ 2 × their threshold, preventing single generic
    keywords from causing false positives in historical sources.
    """
    slugs = classify_text(news.title_original, news.summary_original)

    if source_primary_category:
        text = ((news.title_original or "") + " " + (news.summary_original or "")).lower().strip()
        slugs = [source_primary_category] + [
            s for s in slugs
            if s != source_primary_category
            and _passes_secondary_threshold(s, text)
        ]
        slugs = slugs[:3]

    result = await session.execute(
        select(Category).where(Category.slug.in_(slugs))
    )
    categories = {c.slug: c for c in result.scalars().all()}

    await session.execute(
        delete(news_categories).where(news_categories.c.news_id == news.id)
    )
    if categories:
        await session.execute(
            insert(news_categories),
            [{"news_id": news.id, "category_id": categories[slug].id}
             for slug in slugs if slug in categories],
        )
    return slugs
