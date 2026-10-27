import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Feed News v%s", settings.APP_VERSION)
    await init_db()

    from app.seeds import seed
    await seed()

    from app.scheduler.tasks import start_scheduler, ingestion_task, processing_task
    start_scheduler()

    # Trigger initial ingestion and processing immediately (don't wait for first interval)
    asyncio.create_task(ingestion_task())
    asyncio.create_task(processing_task())

    yield

    from app.scheduler.tasks import stop_scheduler
    stop_scheduler()
    logger.info("Feed News stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Routers
from app.api.news import router as news_router
from app.api.sources import router as sources_router
from app.api.admin import router as admin_router

app.include_router(news_router)
app.include_router(sources_router)
app.include_router(admin_router)


@app.get("/api/categories")
async def list_categories():
    from app.database import AsyncSessionLocal
    from app.models import Category
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category).order_by(Category.order))
        cats = result.scalars().all()
        return [{"id": c.id, "slug": c.slug, "name_es": c.name_es, "icon": c.icon} for c in cats]


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# Serve frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str, request: Request):
        if path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = static_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"error": "not found"}, status_code=404)
