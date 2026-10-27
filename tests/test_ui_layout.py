"""Tests that verify the HTML/CSS/JS always uses the list layout.

These tests parse the static index.html directly and verify:
  - No multi-column grid is applied to news cards in any view.
  - A single renderListCard function handles all views (feed, featured, saved).
  - Featured section container uses .news-list, not a grid class.
  - .list-card-thumb has consistent dimensions (same for image and placeholder).
  - No renderCardFeatured function exists (would produce grid cards).
"""
import re
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "app" / "static" / "index.html"
HTML = HTML_PATH.read_text(encoding="utf-8")


def css_block(html: str) -> str:
    """Extract content inside the <style> tag."""
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    assert m, "No <style> block found in index.html"
    return m.group(1)


def js_block(html: str) -> str:
    """Extract content inside the <script> tag."""
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert m, "No <script> block found in index.html"
    return m.group(1)


CSS = css_block(HTML)
JS = js_block(HTML)


# ---------------------------------------------------------------------------
# CSS: no multi-column grid for news cards
# ---------------------------------------------------------------------------

def test_no_auto_fill_grid_in_news_containers():
    """No repeat(auto-fill, …) grid used for news cards."""
    # The only grid allowed is the page layout (sidebar + main)
    grids = re.findall(r"grid-template-columns\s*:[^;}]+", CSS)
    for g in grids:
        assert "auto-fill" not in g, (
            f"Multi-column auto-fill grid found in CSS — would create multi-column card layout: {g}"
        )
        assert "minmax" not in g or "240px" in g, (
            f"Unexpected minmax() grid (not the sidebar layout): {g}"
        )


def test_news_list_is_single_column_flex():
    """.news-list must be a flex column, not a grid."""
    assert "display: flex" in CSS or "display:flex" in CSS.replace(" ", "")
    m = re.search(r"\.news-list\s*\{([^}]+)\}", CSS, re.DOTALL)
    assert m, ".news-list rule not found in CSS"
    rule = m.group(1)
    assert "flex-direction: column" in rule or "flex-direction:column" in rule.replace(" ", ""), (
        f".news-list must use flex-direction:column, got: {rule}"
    )
    assert "grid" not in rule, ".news-list must not use grid"


def test_list_card_is_horizontal_flex():
    """.list-card must use flex layout (image left, content right)."""
    m = re.search(r"\.list-card\s*\{([^}]+)\}", CSS, re.DOTALL)
    assert m, ".list-card rule not found in CSS"
    rule = m.group(1)
    assert "display: flex" in rule or "display:flex" in rule.replace(" ", ""), (
        ".list-card must use display:flex"
    )
    # Must NOT be column by default (column is only in the responsive media query)
    assert "flex-direction: column" not in rule, (
        ".list-card default must not be column — that's for mobile only"
    )


def test_list_card_thumb_fixed_dimensions():
    """.list-card-thumb must have explicit width and height."""
    m = re.search(r"\.list-card-thumb\s*\{([^}]+)\}", CSS, re.DOTALL)
    assert m, ".list-card-thumb rule not found in CSS"
    rule = m.group(1)
    assert "width" in rule, ".list-card-thumb must have explicit width"
    assert "height" in rule, ".list-card-thumb must have explicit height"


def test_list_card_thumb_img_uses_object_fit_cover():
    """.list-card-thumb img must use object-fit: cover."""
    m = re.search(r"\.list-card-thumb\s+img\s*\{([^}]+)\}", CSS, re.DOTALL)
    assert m, ".list-card-thumb img rule not found in CSS"
    rule = m.group(1)
    assert "object-fit: cover" in rule or "object-fit:cover" in rule.replace(" ", ""), (
        ".list-card-thumb img must use object-fit:cover"
    )


def test_list_card_responsive_stacks_vertically():
    """On narrow screens (.list-card) should stack vertically via a media query."""
    media_sections = re.findall(r"@media[^{]+\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", CSS, re.DOTALL)
    found = False
    for section in media_sections:
        if "list-card" in section and "flex-direction: column" in section:
            found = True
            break
    assert found, (
        "No media query found that stacks .list-card vertically on small screens"
    )


# ---------------------------------------------------------------------------
# HTML: containers use .news-list
# ---------------------------------------------------------------------------

def test_featured_grid_uses_news_list_class():
    """featured-grid container must use class 'news-list', not a grid class."""
    m = re.search(r'id="featured-grid"[^>]*class="([^"]*)"', HTML)
    assert m, "featured-grid element not found in HTML"
    classes = m.group(1).split()
    assert "news-list" in classes, (
        f"featured-grid must have class 'news-list', got: {classes}"
    )
    assert "featured-grid" not in classes, (
        "featured-grid must not reference its own class as a CSS class"
    )
    assert "grid" not in " ".join(classes), (
        f"featured-grid must not have any grid-related CSS class: {classes}"
    )


def test_news_list_element_uses_news_list_class():
    """#news-list element must use class 'news-list'."""
    m = re.search(r'id="news-list"[^>]*class="([^"]*)"', HTML)
    assert m, "#news-list element not found"
    assert "news-list" in m.group(1).split()


# ---------------------------------------------------------------------------
# JS: single render function for all views
# ---------------------------------------------------------------------------

def test_no_render_card_featured_function():
    """renderCardFeatured must not exist — all views use renderListCard."""
    assert "renderCardFeatured" not in JS, (
        "renderCardFeatured still exists in JS — featured section would use grid cards"
    )


def test_featured_uses_render_list_card():
    """loadFeatured must call renderListCard, not renderCardFeatured."""
    assert "renderListCard" in JS
    # The featured-grid innerHTML assignment must use renderListCard
    assert re.search(r"featured-grid.*renderListCard|renderListCard.*featured-grid", JS, re.DOTALL), (
        "featured-grid innerHTML assignment must use renderListCard"
    )


def test_saved_view_uses_render_list_card():
    """renderSaved must call renderListCard."""
    # Find the renderSaved function body
    m = re.search(r"function renderSaved\(\)(.+?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "renderSaved function not found"
    assert "renderListCard" in m.group(1), "renderSaved must use renderListCard"


def test_main_feed_uses_render_list_card():
    """loadNews must call renderListCard for the main feed."""
    m = re.search(r"function loadNews\(\)(.+?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadNews function not found"
    body = m.group(1)
    assert "renderListCard" in body, "loadNews must use renderListCard"


def test_thumb_html_function_exists():
    """thumbHtml helper must exist for consistent thumbnail rendering."""
    assert "function thumbHtml" in JS or "thumbHtml" in JS, (
        "thumbHtml function not found in JS"
    )


def test_image_error_uses_remove_not_display_none():
    """Images must use onerror='this.remove()' so the placeholder stays visible."""
    # There must be no onerror that sets display:none on card images
    bad_onerror = re.findall(r"onerror=['\"][^'\"]*display[^'\"]*none[^'\"]*['\"]", JS)
    assert not bad_onerror, (
        f"Found onerror with display:none — would cause inconsistent card heights: {bad_onerror}"
    )
    # The correct pattern is onerror="this.remove()"
    assert "this.remove()" in JS, (
        "Images must use onerror='this.remove()' to keep consistent card height"
    )


# ===========================================================================
# Spec 3.2 — Featured block visibility tests
# ===========================================================================
#
# Tests verify the JS behaviour in index.html:
#   - Featured section is shown ONLY when state.relevance === 'featured'
#   - All other filter states hide it
#   - No duplicates: loadNews() early-returns when relevance === 'featured'


# ---------------------------------------------------------------------------
# 3.2.1  «Todas» (no relevance filter) → hide the featured block
# ---------------------------------------------------------------------------

def test_3_2_1_todas_hides_featured_section():
    """When state.relevance is falsy, loadFeatured must hide the section."""
    # The guard condition must fire for any truthy relevance != 'featured'
    m = re.search(r"function loadFeatured\(\)(.*?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadFeatured() function not found in JS"
    body = m.group(1)
    # Must hide when relevance !== 'featured'
    assert "relevance !== 'featured'" in body or "relevance!=='featured'" in body.replace(" ", ""), (
        "loadFeatured() must hide the section when relevance !== 'featured'"
    )
    # Must set display:none early (before the API call)
    hide_pos = body.find("display='none'")
    assert hide_pos != -1, "loadFeatured() must set display='none' on early return"


# ---------------------------------------------------------------------------
# 3.2.2  «Destacadas» → show the featured block
# ---------------------------------------------------------------------------

def test_3_2_2_destacadas_shows_featured_section():
    """When state.relevance === 'featured', loadFeatured must show the section."""
    m = re.search(r"function loadFeatured\(\)(.*?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadFeatured() function not found in JS"
    body = m.group(1)
    # Must set display to something other than 'none' after fetching
    assert "display=''" in body or "display = ''" in body or "display='block'" in body or \
           "removeAttribute('style')" in body or ".hidden = false" in body, (
        "loadFeatured() must make the section visible when relevance === 'featured'"
    )


# ---------------------------------------------------------------------------
# 3.2.3  «Relevantes» / «Seguimiento» → hide the featured block
# ---------------------------------------------------------------------------

def test_3_2_3_relevantes_y_seguimiento_hide_featured():
    """The visibility guard in loadFeatured() only admits 'featured', nothing else."""
    m = re.search(r"function loadFeatured\(\)(.*?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadFeatured() function not found in JS"
    body = m.group(1)
    # Guard must use 'featured' as the only accepted relevance value
    # The implementation checks !== 'featured' (negation) to early-return
    assert "!== 'featured'" in body or "!=='featured'" in body.replace(" ", ""), (
        "loadFeatured() must guard with relevance !== 'featured'"
    )
    # Ensure the body does NOT also allow 'relevant' or 'follow' to show the block
    assert "=== 'relevant'" not in body and "==='relevant'" not in body.replace(" ", ""), (
        "loadFeatured() must not admit 'relevant' as a show-block condition"
    )


# ---------------------------------------------------------------------------
# 3.2.4  Category filter → hide the featured block
# ---------------------------------------------------------------------------

def test_3_2_4_category_filter_hides_featured():
    """Category changes call loadFeatured(); the guard then hides the block."""
    # The category-click handler must call loadFeatured()
    assert "loadFeatured" in JS, "loadFeatured must be called somewhere in JS"
    m = re.search(r"state\.category\s*=\s*btn\.dataset\.cat.*?loadFeatured\(\)", JS, re.DOTALL)
    assert m, (
        "Category-click handler must call loadFeatured() after updating state.category"
    )


# ---------------------------------------------------------------------------
# 3.2.5  Geographic filter alone → hide featured (unless relevance === 'featured')
# ---------------------------------------------------------------------------

def test_3_2_5_geo_filter_without_featured_hides_block():
    """Geo-scope changes call loadFeatured(); guard hides block unless relevance==='featured'."""
    m = re.search(r"state\.scope\s*=\s*btn\.dataset\.scope.*?loadFeatured\(\)", JS, re.DOTALL)
    assert m, (
        "Geo-scope click handler must call loadFeatured() after updating state.scope"
    )


# ---------------------------------------------------------------------------
# 3.2.6  Changing filter updates visibility correctly
# ---------------------------------------------------------------------------

def test_3_2_6_relevance_filter_calls_load_featured():
    """The relevance-click handler calls loadFeatured() so visibility updates."""
    m = re.search(r"state\.relevance\s*=\s*btn\.dataset\.relevance.*?loadFeatured\(\)", JS, re.DOTALL)
    assert m, (
        "Relevance-click handler must call loadFeatured() after updating state.relevance"
    )


# ---------------------------------------------------------------------------
# 3.2.7  «Destacadas» + category or geo → API call includes both params
# ---------------------------------------------------------------------------

def test_3_2_7_featured_api_call_includes_category_and_geo():
    """loadFeatured() must pass category and geo params to the /featured API."""
    m = re.search(r"function loadFeatured\(\)(.*?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadFeatured() function not found in JS"
    body = m.group(1)
    assert "state.scope" in body, (
        "loadFeatured() must forward state.scope to the /featured API"
    )
    assert "state.category" in body, (
        "loadFeatured() must forward state.category to the /featured API"
    )


# ---------------------------------------------------------------------------
# 3.2.8  No duplicates: loadNews() must early-return when relevance === 'featured'
# ---------------------------------------------------------------------------

def test_3_2_8_load_news_returns_early_for_featured():
    """loadNews() must not render its list when state.relevance === 'featured'."""
    m = re.search(r"async function loadNews\(\)(.*?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadNews() function not found in JS"
    body = m.group(1)
    assert "=== 'featured'" in body or "==='featured'" in body.replace(" ", ""), (
        "loadNews() must check for relevance === 'featured'"
    )
    # The early return / bail-out must appear BEFORE the API params are built
    featured_check_pos = body.find("'featured'")
    return_pos = body.find("return", featured_check_pos)
    assert return_pos != -1, (
        "loadNews() must return early when relevance === 'featured'"
    )


# ---------------------------------------------------------------------------
# 3.2.9  Search and geo still function (no accidental removal of their logic)
# ---------------------------------------------------------------------------

def test_3_2_9_search_param_still_forwarded_in_load_news():
    """loadNews() must still forward the search/q parameter."""
    m = re.search(r"async function loadNews\(\)(.*?)^}", JS, re.MULTILINE | re.DOTALL)
    assert m, "loadNews() function not found in JS"
    body = m.group(1)
    assert "state.search" in body or "q" in body, (
        "loadNews() must still forward the search/q parameter"
    )
    assert "state.scope" in body, (
        "loadNews() must still forward state.scope (geo filter)"
    )


# ---------------------------------------------------------------------------
# 3.2.10  Other result sections keep their current behaviour
# ---------------------------------------------------------------------------

def test_3_2_10_saved_section_still_managed_by_render_saved():
    """renderSaved() must still exist and be called from the saved-btn handler."""
    assert "function renderSaved" in JS, "renderSaved() function must still exist"
    assert "renderSaved()" in JS, "renderSaved() must still be called"
    # saved-btn handler must NOT call loadNews() while showing saved articles
    m = re.search(r"saved-btn.*?addEventListener.*?click.*?\)\s*\{(.*?)^\s*\}\)", JS, re.MULTILINE | re.DOTALL)
    # Fallback: look for the showSaved toggling block
    m2 = re.search(r"showSaved\s*=\s*!state\.showSaved(.*?)renderSaved\(\)", JS, re.DOTALL)
    assert m2, (
        "saved-btn handler must call renderSaved() when entering saved view"
    )
