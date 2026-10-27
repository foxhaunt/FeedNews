import re
from typing import Optional
from app.ingestion.rss_fetcher import RawArticle


_SPAM_PATTERNS = [
    re.compile(r"\b(subscribe|newsletter|sign up|click here|buy now)\b", re.I),
]

# ─── Editorial recommendation block cleaner ──────────────────────────────────
# Spanish CMSs inject "Más información: <headline>" or "Otras historias: …" at
# the end of RSS summary fields.  These patterns match from the first editorial
# marker to end-of-string and strip the whole block.
#
# Rules to avoid false positives:
#  - All markers are Title-case (capital first letter) – legitimate mid-sentence
#    uses ("para más información, consulte…") use lowercase and are unaffected.
#  - A literal colon must follow (possibly with a space before it), which
#    distinguishes the section-heading use from any prose occurrence.
#  - `re.DOTALL` ensures multi-line / multi-headline blocks are fully removed.

_EDITORIAL_MARKERS = (
    r"Más información"
    r"|Otras historias"
    r"|Otros artículos"
    r"|Relacionado"
    r"|Te puede interesar"
    r"|También te puede interesar"
    r"|Lee también"
    r"|Ver también"
    r"|No te pierdas"
    r"|En otros medios"
    r"|Sigue leyendo"
    r"|Últimas noticias"
)

# Match: optional leading whitespace + marker + optional space + colon + everything after
_EDITORIAL_BLOCK_RE = re.compile(
    r"\s*(?:" + _EDITORIAL_MARKERS + r")\s*:.*",
    re.DOTALL,
)

# HTML-level: remove <p>/<li>/<div> tags whose text content starts with a marker
_EDITORIAL_HTML_RE = re.compile(
    r"<(?:p|li|div)[^>]*>\s*(?:" + _EDITORIAL_MARKERS + r")\s*:.*?</(?:p|li|div)>",
    re.IGNORECASE | re.DOTALL,
)


def clean_editorial_noise(text: Optional[str]) -> Optional[str]:
    """Remove editorial recommendation blocks from plain text.

    Strips everything from the first occurrence of a known editorial marker
    (e.g. 'Más información:', 'Otras historias:') to the end of the string.
    Only Title-case markers are matched, so mid-sentence lowercase uses like
    'para más información, consulte…' are preserved unchanged.
    """
    if not text:
        return text
    cleaned = _EDITORIAL_BLOCK_RE.sub("", text).strip()
    return cleaned or text  # never return empty string if input was non-empty


def clean_html_editorial_noise(html: Optional[str]) -> Optional[str]:
    """Strip editorial recommendation blocks from HTML before text extraction."""
    if not html:
        return html
    return _EDITORIAL_HTML_RE.sub("", html)


def is_valid_article(article: RawArticle) -> bool:
    if not article.title or len(article.title.strip()) < 10:
        return False
    if not article.url or not article.url.startswith("http"):
        return False
    return True


def normalize_url(url: str) -> str:
    """Strip tracking params while keeping essential ones."""
    from urllib.parse import urlparse, urlencode, parse_qsl
    try:
        p = urlparse(url)
        keep_params = {}
        for k, v in parse_qsl(p.query):
            if k.lower() not in (
                "utm_source", "utm_medium", "utm_campaign", "utm_content",
                "utm_term", "ref", "via", "source", "fbclid", "gclid",
                "mc_cid", "mc_eid", "_ga"
            ):
                keep_params[k] = v
        clean_query = urlencode(keep_params) if keep_params else ""
        clean = p._replace(query=clean_query, fragment="")
        return clean.geturl()
    except Exception:
        return url


def _word_in(word: str, text: str) -> bool:
    """True if *word* appears as a complete word (or phrase) in *text* (case-insensitive)."""
    return bool(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text, re.IGNORECASE))


# ─── Spain keywords ─────────────────────────────────────────────────────────
# ONLY terms that are unique to Spain; generic political vocabulary
# ("congreso", "senado", "presidente", "rey", "pp"…) is intentionally excluded
# because those words appear in journalism about any country.
_SPAIN_TERMS = [
    # Geography — Spain-specific place names (exact word match)
    "españa", "español", "española", "españoles", "españolas",
    "madrid", "barcelona", "bilbao", "sevilla", "zaragoza",
    "málaga", "granada", "alicante", "murcia", "donostia",
    "comunidad autónoma", "autonomía española",
    "moncloa",
    # Spain-specific institutions (qualified phrases, not generic words)
    "congreso de los diputados",
    "senado de españa", "senado español",
    "cortes generales",
    "tribunal constitucional español", "tribunal constitucional de españa",
    "tribunal supremo de españa", "tribunal supremo español",
    "banco de españa",
    "agencia tributaria española",
    "boe",          # Boletín Oficial del Estado
    "guardia civil",
    "gobierno de españa", "gobierno español", "ejecutivo español",
    # Spain-specific parties (proper nouns in Spanish political context)
    "psoe", "partido socialista obrero español",
    "partido popular español",
    "ciudadanos partido",
    # Require "vox" to appear as a Spain party, not other uses of the word
    "partido vox", "vox partido", "líder de vox", "vox en españa",
    # Spain-specific political figures
    "pedro sánchez", "feijóo", "núñez feijóo",
    "yolanda díaz", "isabel díaz ayuso", "ayuso",
    "abascal", "calvo soriano",
    # Spain-specific royals — use full titles, not bare "rey" or "reina"
    "rey felipe", "reina letizia", "felipe vi", "casa real española",
    # Spain-specific economic/institutional terms
    "seguridad social española",
]

# ─── Europe keywords ─────────────────────────────────────────────────────────
_EUROPE_TERMS = [
    "unión europea", "union europea",
    "parlamento europeo",
    "comisión europea", "consejo europeo",
    "banco central europeo", "bce",
    "bruselas", "estrasburgo",
    "otan", "nato",         # Western alliance — primarily Europe-related
    "schengen",
    # European countries (Spain is deliberately excluded — covered above)
    "alemania", "berlin", "hamburgo", "múnich", "munich",
    "francia", "paris", "paris ",
    "italia", "roma", "milan",
    "reino unido", "gran bretaña", "londres",
    "ucrania", "kiev",
    "polonia", "varsovia",
    "países bajos", "holanda",
    "bélgica",
    "austria", "viena",
    "suecia", "estocolmo",
    "noruega", "oslo",
    "suiza", "ginebra",
    "portugal", "lisboa",
    "grecia", "atenas",
    "hungría", "budapest",
    "chequia", "república checa",
    "rumania", "bucarest",
    # European leaders (as of 2025)
    "macron", "scholz", "meloni", "von der leyen", "ursula",
    "zelenski", "zelensky",
    # English variants
    "european union", "european parliament", "european commission",
    "european central bank", "nato summit",
    "germany", "france", "italy", "ukraine", "poland",
    "united kingdom", "britain", "london",
    "brussels", "strasbourg",
]


def extract_geo_hints(title: str, summary: Optional[str]) -> list:
    """Return a list with the most specific geographic scope inferred from content.

    Rules:
    - Spain:         event explicitly involves Spain or Spanish-specific entities.
    - Europe:        event involves European countries, EU institutions, or NATO.
    - International: everything else (default when content is ambiguous).

    Language of the article and source domain are NOT used as criteria.
    """
    text = (title or "") + " " + (summary or "")

    for term in _SPAIN_TERMS:
        if _word_in(term, text):
            return ["spain"]

    for term in _EUROPE_TERMS:
        if _word_in(term, text):
            return ["europe"]

    return ["international"]
