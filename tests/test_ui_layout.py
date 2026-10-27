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
