from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from app.database import create_engine, create_session_factory
from app.models.foreshadowing import Foreshadowing, ForeshadowingStatus
from app.models.story import Story
from app.config import settings

router = APIRouter(prefix="/api/foreshadowing", tags=["foreshadowing"])


def _get_db_path(story_id: str) -> str:
    return str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite")


@router.get("/{story_id}")
async def list_foreshadowings(story_id: str, status: str = ""):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            query = select(Foreshadowing).where(Foreshadowing.story_id == story_id)
            if status:
                query = query.where(Foreshadowing.status == status)
            query = query.order_by(Foreshadowing.priority.desc())
            result = await db.execute(query)
            items = result.scalars().all()
            return {
                "foreshadowings": [
                    {
                        "id": f.id,
                        "title": f.title,
                        "description": f.description,
                        "plant_chapter_id": f.plant_chapter_id,
                        "reveal_chapter_id": f.reveal_chapter_id,
                        "status": f.status.value if f.status else "planted",
                        "priority": f.priority,
                        "related_entries": f.related_entries,
                        "notes": f.notes,
                        "created_at": f.created_at.isoformat(),
                        "updated_at": f.updated_at.isoformat(),
                    }
                    for f in items
                ]
            }
    finally:
        await engine.dispose()


@router.post("/{story_id}")
async def create_foreshadowing(story_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            fp = Foreshadowing(
                story_id=story_id,
                title=data.get("title", ""),
                description=data.get("description", ""),
                plant_chapter_id=data.get("plant_chapter_id"),
                status=data.get("status", ForeshadowingStatus.planted),
                priority=data.get("priority", 3),
                related_entries=data.get("related_entries", []),
                notes=data.get("notes", ""),
            )
            db.add(fp)
            await db.commit()
            return {"ok": True, "id": fp.id}
    finally:
        await engine.dispose()


@router.put("/{story_id}/{fp_id}")
async def update_foreshadowing(story_id: str, fp_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            fp = await db.get(Foreshadowing, fp_id)
            if not fp:
                raise HTTPException(status_code=404, detail="Not found")
            for field in ["title", "description", "status", "priority", "related_entries", "notes",
                           "plant_chapter_id", "reveal_chapter_id"]:
                if field in data:
                    setattr(fp, field, data[field])
            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.delete("/{story_id}/{fp_id}")
async def delete_foreshadowing(story_id: str, fp_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            fp = await db.get(Foreshadowing, fp_id)
            if fp:
                await db.delete(fp)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()
