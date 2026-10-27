"""Tests for API endpoints using a dedicated test database."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def test_app():
    """Create app with in-memory test database, bypassing lifespan."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.database import Base
    import app.models  # noqa: registers all models

    engine = create_async_engine(TEST_DB, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    # Seed categories
    from app.models import Category, Source
    from sqlalchemy import select
    CATS = [
        {"slug": "politica", "name_es": "Política", "name_en": "Politics", "icon": "🏛️", "order": 1},
        {"slug": "economia", "name_es": "Economía", "name_en": "Economy", "icon": "📈", "order": 2},
    ]
    async with SessionLocal() as session:
        for c in CATS:
            ex = (await session.execute(select(Category).where(Category.slug == c["slug"]))).scalar_one_or_none()
            if not ex:
                session.add(Category(**c))
        await session.commit()

    # Create minimal app without full lifespan
    from fastapi import FastAPI
    from app.api.news import router as news_router
    from app.api.sources import router as sources_router
    from app.api.admin import router as admin_router
    from app.database import get_db
    from app.config import settings

    mini_app = FastAPI()
    mini_app.include_router(news_router)
    mini_app.include_router(sources_router)
    mini_app.include_router(admin_router)

    @mini_app.get("/api/categories")
    async def list_categories(db: AsyncSession = __import__('fastapi').Depends(override_get_db)):
        from sqlalchemy import select
        result = await db.execute(select(Category).order_by(Category.order))
        cats = result.scalars().all()
        return [{"id": c.id, "slug": c.slug, "name_es": c.name_es, "icon": c.icon} for c in cats]

    @mini_app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "test"}

    mini_app.dependency_overrides[get_db] = override_get_db

    yield mini_app, SessionLocal
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_app):
    app, _ = test_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_categories_endpoint(client):
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_news_list_empty(client):
    resp = await client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_sources_list(client):
    resp = await client.get("/api/sources")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_stats_requires_token(client):
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_with_token(client):
    from app.config import settings
    resp = await client.get("/api/admin/stats", headers={"X-Admin-Token": settings.ADMIN_TOKEN})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_news" in data
    assert "total_sources" in data


@pytest.mark.asyncio
async def test_news_404(client):
    resp = await client.get("/api/news/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_news_filter_by_geo(client):
    resp = await client.get("/api/news?geo=spain")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_news_filter_by_relevance(client):
    resp = await client.get("/api/news?relevance=featured")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_news_search(client):
    resp = await client.get("/api/news?q=gobierno")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_news_pagination(client):
    resp = await client.get("/api/news?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_create_source_requires_admin(client):
    resp = await client.post("/api/sources", json={
        "name": "Test Feed", "url": "https://test.com/rss"
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_source_with_admin(client):
    from app.config import settings
    resp = await client.post(
        "/api/sources",
        json={"name": "Test Feed", "url": "https://test-unique-url.com/rss", "geographic_scope": "spain"},
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Feed"
    assert data["geographic_scope"] == "spain"


@pytest.mark.asyncio
async def test_news_sort_options(client):
    for sort in ("relevance", "published_at"):
        resp = await client.get(f"/api/news?sort_by={sort}")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_featured_news_endpoint(client):
    resp = await client.get("/api/news/featured")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_diversity_endpoint_requires_token(client):
    resp = await client.get("/api/admin/diversity")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_diversity_endpoint_returns_structure(client):
    from app.config import settings
    resp = await client.get(
        "/api/admin/diversity",
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_articles" in data
    assert "editorial_distribution" in data
    assert "scope_distribution" in data
    assert "concentration_index_hhi" in data
    assert "concentration_label" in data
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_diversity_hhi_range(client):
    """HHI must be between 0 and 1 (inclusive)."""
    from app.config import settings
    resp = await client.get(
        "/api/admin/diversity",
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )
    assert resp.status_code == 200
    hhi = resp.json()["concentration_index_hhi"]
    assert 0.0 <= hhi <= 1.0


@pytest.mark.asyncio
async def test_diversity_concentration_label_valid(client):
    from app.config import settings
    resp = await client.get(
        "/api/admin/diversity",
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )
    label = resp.json()["concentration_label"]
    assert label in ("alta", "moderada", "baja")
