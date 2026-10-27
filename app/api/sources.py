from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.models import Source
from app.schemas import SourceOut, SourceCreate
from app.config import settings

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _check_admin(x_admin_token: Optional[str] = Header(None)):
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=List[SourceOut])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).order_by(Source.geographic_scope, Source.name))
    return result.scalars().all()


@router.post("", response_model=SourceOut)
async def create_source(
    data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)
    source = Source(**data.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/{source_id}/toggle", response_model=SourceOut)
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.enabled = not source.enabled
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/{source_id}/fetch")
async def trigger_fetch(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    x_admin_token: Optional[str] = Header(None),
):
    _check_admin(x_admin_token)
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    from app.ingestion.manager import ingest_source
    import asyncio
    asyncio.create_task(ingest_source(source_id))
    return {"status": "fetch_triggered", "source_id": source_id}
