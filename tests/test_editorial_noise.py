"""Tests for the editorial recommendation block cleaner.

Verifies that CMS-injected "Más información:", "Otras historias:", etc. blocks
are stripped from RSS summaries without touching legitimate content.
"""
import pytest
from app.ingestion.normalizer import clean_editorial_noise, clean_html_editorial_noise


# ── Helpers ──────────────────────────────────────────────────────────────────

def clean(text):
    return clean_editorial_noise(text)


# ── Spec example (verbatim from the bug report) ──────────────────────────────

def test_spec_otras_historias():
    """Exact example from the bug report: 'Otras historias:' block removed."""
    raw = (
        "Decenas de perfiles en redes sociales piden llevar a cabo nuevos altercados "
        "en Barcelona, Madrid, Málaga o Bilbao, entre otras ciudades.  Otras historias: "
        "  La otra guerra que sí gana Marruecos a España: del tomate a la fresa en el "
        "Sáhara gracias a la UE y Pedro Sánchez"
    )
    result = clean(raw)
    assert result == (
        "Decenas de perfiles en redes sociales piden llevar a cabo nuevos altercados "
        "en Barcelona, Madrid, Málaga o Bilbao, entre otras ciudades."
    )
    assert "Otras historias" not in result
    assert "Marruecos" not in result


# ── 'Más información:' ────────────────────────────────────────────────────────

def test_mas_informacion_colon():
    """'Más información:' block stripped, preceding sentence preserved."""
    raw = (
        "72 de los arrestados son menores de edad. "
        "Collboni promete perseguir a todos los vándalos. "
        "Más información:   Cientos de miles desafían a Macron."
    )
    result = clean(raw)
    assert "Más información" not in result
    assert "Cientos de miles" not in result
    assert "Collboni promete" in result


def test_mas_informacion_space_before_colon():
    """'Más información :' (space before colon) is also stripped."""
    raw = (
        "El CM del Partido Popular se ha convertido en protagonista. "
        'Más información :  "Si cobrar mordidas es de zurdos, soy zurdo"'
    )
    result = clean(raw)
    assert "Más información" not in result
    assert "soy zurdo" not in result
    assert "protagonista" in result


def test_mas_informacion_single_headline():
    """Single headline after marker is removed."""
    raw = "La intervención ha durado media hora. Más información:   La Princesa Leonor defiende el papel de las mujeres."
    result = clean(raw)
    assert "Más información" not in result
    assert "Leonor" not in result
    assert "media hora" in result


def test_mas_informacion_multiple_headlines():
    """Multiple headlines after marker are all removed."""
    raw = (
        "Resumen legítimo del artículo sobre política española. "
        "Más información:   Título del artículo uno.  "
        "Título del artículo dos.  Título del artículo tres."
    )
    result = clean(raw)
    assert "Más información" not in result
    assert "artículo uno" not in result
    assert "artículo tres" not in result
    assert "política española" in result


# ── Other markers ─────────────────────────────────────────────────────────────

def test_relacionado_colon():
    raw = "El gobierno aprueba el presupuesto. Relacionado:   El Congreso debate los impuestos."
    result = clean(raw)
    assert "Relacionado" not in result
    assert "presupuesto" in result


def test_te_puede_interesar():
    raw = "Una investigación revela datos sobre el clima. Te puede interesar:   Guía para entender el cambio climático."
    result = clean(raw)
    assert "Te puede interesar" not in result
    assert "investigación" in result


def test_lee_tambien():
    raw = "El Barcelona gana 3-0 al Real Madrid. Lee también:   Análisis del partido de la semana."
    result = clean(raw)
    assert "Lee también" not in result
    assert "gana 3-0" in result


def test_ver_tambien():
    raw = "La tasa de paro baja al 10%. Ver también:   Cómo afecta el paro al sistema de pensiones."
    result = clean(raw)
    assert "Ver también" not in result
    assert "paro baja" in result


def test_ultimas_noticias():
    raw = "La cumbre del G7 concluye con acuerdos. Últimas noticias:   Borrell pide más sanciones."
    result = clean(raw)
    assert "Últimas noticias" not in result
    assert "G7 concluye" in result


def test_no_te_pierdas():
    raw = "El nuevo iPhone supera al modelo anterior. No te pierdas:   Comparativa de todos los modelos."
    result = clean(raw)
    assert "No te pierdas" not in result
    assert "supera al modelo" in result


def test_sigue_leyendo():
    raw = "El Tribunal Supremo ratifica la condena. Sigue leyendo:   Los detalles del fallo judicial."
    result = clean(raw)
    assert "Sigue leyendo" not in result
    assert "ratifica la condena" in result


def test_en_otros_medios():
    raw = "La noticia sobre el accidente aéreo. En otros medios:   The Guardian recoge la tragedia."
    result = clean(raw)
    assert "En otros medios" not in result
    assert "accidente aéreo" in result


def test_otros_articulos():
    raw = "La reforma laboral avanza en el Congreso. Otros artículos:   Cronología de la reforma."
    result = clean(raw)
    assert "Otros artículos" not in result
    assert "avanza en el Congreso" in result


# ── False positive guards — legitimate mid-text uses ─────────────────────────

def test_lowercase_mas_informacion_not_stripped():
    """'más información' (lowercase) mid-sentence is NOT stripped."""
    raw = "Para más información sobre el tema, visite la web oficial del ministerio."
    result = clean(raw)
    assert result == raw


def test_lowercase_relacionado_not_stripped():
    """'relacionado' (lowercase, no colon) in body text is NOT stripped."""
    raw = "El hecho está relacionado con la crisis energética europea de 2022."
    result = clean(raw)
    assert result == raw


def test_ver_tambien_lowercase_not_stripped():
    """'ver también' lowercase in body text is preserved."""
    raw = "Conviene ver también las cifras del año anterior para contextualizar."
    result = clean(raw)
    assert result == raw


def test_sigue_leyendo_lowercase_not_stripped():
    """'sigue leyendo' as part of a sentence is preserved."""
    raw = "El lector sigue leyendo el periódico digital en su tablet."
    result = clean(raw)
    assert result == raw


def test_mas_informacion_without_colon_not_stripped():
    """'Más información' without a following colon is NOT stripped."""
    raw = "El artículo proporciona Más información relevante sobre el caso judicial."
    result = clean(raw)
    assert result == raw


def test_lee_tambien_without_colon_not_stripped():
    """'Lee también' without colon is preserved."""
    raw = "El alumno lee también los capítulos complementarios del libro."
    result = clean(raw)
    assert result == raw


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_none_input():
    assert clean(None) is None


def test_empty_string():
    result = clean("")
    assert result == "" or result is None or result == ""


def test_clean_summary_unchanged():
    """A summary with no editorial markers passes through unchanged."""
    raw = "El presidente anuncia un nuevo plan de inversión en infraestructuras por valor de 3.000 millones."
    assert clean(raw) == raw


def test_marker_at_very_start():
    """If the entire summary IS the marker block, the original is returned unchanged.

    There is no legitimate content before the marker, so stripping it would
    leave an empty string.  clean_editorial_noise prefers to keep the original
    rather than returning an empty summary that could hide the article.
    """
    raw = "Más información:   Artículo relacionado sobre la crisis."
    result = clean(raw)
    # The original is returned as-is (no legitimate content to preserve)
    assert result == raw


def test_whitespace_only_before_marker():
    """Marker preceded only by whitespace is stripped along with the whitespace."""
    raw = "Resumen real del artículo.\n  \nOtras historias:   Noticia dos. Noticia tres."
    result = clean(raw)
    assert "Otras historias" not in result
    assert "Noticia dos" not in result
    assert "Resumen real" in result


# ── HTML-level cleaning ────────────────────────────────────────────────────────

def test_html_editorial_block_in_paragraph():
    """<p> containing 'Más información:' is removed from HTML before text extraction."""
    html = (
        "<p>Resumen legítimo del artículo sobre economía.</p>"
        "<p>Más información:  <a href='http://example.com'>Noticia relacionada</a></p>"
    )
    cleaned_html = clean_html_editorial_noise(html)
    assert "Más información" not in cleaned_html
    assert "Noticia relacionada" not in cleaned_html
    assert "Resumen legítimo" in cleaned_html


def test_html_otras_historias_in_li():
    """<li> containing 'Otras historias:' is removed."""
    html = (
        "<p>El gobierno presenta el presupuesto.</p>"
        "<li>Otras historias:  <a href='http://example.com'>Otro artículo</a></li>"
    )
    cleaned_html = clean_html_editorial_noise(html)
    assert "Otras historias" not in cleaned_html
    assert "presupuesto" in cleaned_html


def test_html_clean_content_unchanged():
    """HTML without editorial markers passes through unchanged."""
    html = "<p>Texto limpio sobre noticias internacionales.</p><p>Segunda frase del resumen.</p>"
    assert clean_html_editorial_noise(html) == html


def test_html_none_input():
    assert clean_html_editorial_noise(None) is None
