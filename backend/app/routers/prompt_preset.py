import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from app.database import Base, create_engine, create_session_factory
from app.models.prompt_preset import PromptPreset, PromptRole
from app.utils.prompt_templates import (
    CONTINUATION_SYSTEM, CONTINUATION_USER, DIRECTED_CONTINUATION_USER,
    POLISHING_SYSTEM, POLISHING_USER,
    SUMMARY_SMALL_PROMPT, SUMMARY_LARGE_PROMPT,
    WORLD_ANALYSIS_PROMPT,
    FORESHADOWING_DETECTION,
)
from app.config import settings

router = APIRouter(prefix="/api/prompt-presets", tags=["prompt_presets"])
INDEX_DB = str(Path(settings.data_dir) / "index.sqlite")

_DEFAULT_PRESETS = {
    PromptRole.continuation_system: ("系统提示词 - 续写", CONTINUATION_SYSTEM),
    PromptRole.polishing_system: ("系统提示词 - 润色", POLISHING_SYSTEM),
    PromptRole.small_summary_user: ("任务提示词 - 小总结", SUMMARY_SMALL_PROMPT),
    PromptRole.large_summary_user: ("任务提示词 - 大总结", SUMMARY_LARGE_PROMPT),
    PromptRole.world_analysis_user: ("任务提示词 - 世界书分析", WORLD_ANALYSIS_PROMPT),
    PromptRole.foreshadowing_user: ("任务提示词 - 伏笔检测", FORESHADOWING_DETECTION),
    PromptRole.continuation_user: ("任务提示词 - 续写", CONTINUATION_USER),
}


async def _ensure_db():
    engine = create_engine(INDEX_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def seed_defaults(db):
    """Seed built-in prompt presets if not already present."""
    for role, (name, content) in _DEFAULT_PRESETS.items():
        result = await db.execute(
            select(PromptPreset).where(
                PromptPreset.role == role,
                PromptPreset.is_default == True,
            )
        )
        if not result.scalar_one_or_none():
            db.add(PromptPreset(
                id=str(uuid.uuid4()),
                name=name,
                role=role,
                content=content,
                is_default=True,
            ))


@router.get("/")
async def list_presets(role: str = ""):
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            await seed_defaults(db)
            await db.commit()

            query = select(PromptPreset)
            if role:
                query = query.where(PromptPreset.role == role)
            query = query.order_by(PromptPreset.is_default.desc(), PromptPreset.created_at.desc())
            result = await db.execute(query)
            return {
                "presets": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "role": p.role.value,
                        "content": p.content,
                        "is_default": p.is_default,
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in result.scalars().all()
                ]
            }
    finally:
        await engine.dispose()


@router.post("/")
async def create_preset(request: Request):
    data = await request.json()
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            preset = PromptPreset(
                id=str(uuid.uuid4()),
                name=data.get("name", ""),
                role=data.get("role", "continuation_system"),
                content=data.get("content", ""),
                is_default=False,
            )
            db.add(preset)
            await db.commit()
            return {"ok": True, "id": preset.id}
    finally:
        await engine.dispose()


@router.put("/{preset_id}")
async def update_preset(preset_id: str, request: Request):
    data = await request.json()
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            preset = await db.get(PromptPreset, preset_id)
            if not preset:
                raise HTTPException(status_code=404, detail="Not found")
            if preset.is_default and "content" not in data:
                raise HTTPException(status_code=400, detail="Cannot rename default presets")
            for field in ["name", "content"]:
                if field in data:
                    setattr(preset, field, data[field])
            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str):
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            preset = await db.get(PromptPreset, preset_id)
            if preset and not preset.is_default:
                await db.delete(preset)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()
