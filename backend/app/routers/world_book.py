import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from app.database import create_engine, create_session_factory
from app.models.world_book import WorldBookEntry, CharacterRelation, EntryCategory
from app.models.model_config import ModelRole
from app.config import settings

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.providers.registry import ProviderRegistry
from app.utils.prompt_templates import WORLD_ASSIST_SYSTEM_PROMPT
from app.utils.model_fallback import get_model_config

registry = ProviderRegistry()

router = APIRouter(prefix="/api/world-book", tags=["world_book"])


def _get_db_path(story_id: str) -> str:
    return str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite")


@router.get("/{story_id}")
async def list_entries(story_id: str, category: str = ""):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            query = select(WorldBookEntry).where(WorldBookEntry.story_id == story_id)
            if category:
                query = query.where(WorldBookEntry.category == category)
            query = query.order_by(WorldBookEntry.importance.desc())
            result = await db.execute(query)
            entries = result.scalars().all()
            return {
                "entries": [
                    {
                        "id": e.id,
                        "category": e.category.value,
                        "name": e.name,
                        "description": e.description,
                        "aliases": e.aliases,
                        "attributes": e.attributes,
                        "importance": e.importance,
                        "sort_order": e.sort_order,
                        "status": e.status.value if e.status else "active",
                        "version": e.version,
                        "source_chapter_id": e.source_chapter_id,
                        "updated_at": e.updated_at.isoformat(),
                    }
                    for e in entries
                ]
            }
    finally:
        await engine.dispose()


@router.get("/{story_id}/{entry_id}")
async def get_entry(story_id: str, entry_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            entry = await db.get(WorldBookEntry, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            # Get relations for character entries
            relations = []
            if entry.category == EntryCategory.character:
                rel_result = await db.execute(
                    select(CharacterRelation).where(
                        (CharacterRelation.source_char_id == entry_id)
                        | (CharacterRelation.target_char_id == entry_id)
                    )
                )
                for rel in rel_result.scalars().all():
                    other_id = rel.target_char_id if rel.source_char_id == entry_id else rel.source_char_id
                    other = await db.get(WorldBookEntry, other_id)
                    relations.append({
                        "id": rel.id,
                        "other_name": other.name if other else "",
                        "other_id": other_id,
                        "relation_type": rel.relation_type,
                        "description": rel.description,
                        "intensity": rel.intensity,
                        "direction": "outgoing" if rel.source_char_id == entry_id else "incoming",
                    })

            return {
                "id": entry.id,
                "category": entry.category.value,
                "name": entry.name,
                "description": entry.description,
                "aliases": entry.aliases,
                "attributes": entry.attributes,
                "importance": entry.importance,
                "status": entry.status.value if entry.status else "active",
                "version": entry.version,
                "source_chapter_id": entry.source_chapter_id,
                "relations": relations,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
    finally:
        await engine.dispose()


@router.put("/{story_id}/{entry_id}")
async def update_entry(story_id: str, entry_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            entry = await db.get(WorldBookEntry, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            for field in ["name", "description", "aliases", "attributes", "importance", "sort_order", "status", "category"]:
                if field in data:
                    setattr(entry, field, data[field])

            entry.version += 1
            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.delete("/{story_id}/{entry_id}")
async def delete_entry(story_id: str, entry_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            entry = await db.get(WorldBookEntry, entry_id)
            if entry:
                await db.delete(entry)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.post("/{story_id}/relations")
async def create_relation(story_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            relation = CharacterRelation(
                story_id=story_id,
                source_char_id=data["source_char_id"],
                target_char_id=data["target_char_id"],
                relation_type=data.get("relation_type", ""),
                description=data.get("description", ""),
                intensity=data.get("intensity", 5),
            )
            db.add(relation)
            await db.commit()
            return {"ok": True, "id": relation.id}
    finally:
        await engine.dispose()


@router.delete("/{story_id}/relations/{relation_id}")
async def delete_relation(story_id: str, relation_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            rel = await db.get(CharacterRelation, relation_id)
            if rel:
                await db.delete(rel)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.post("/{story_id}/assist-stream")
async def assist_stream(story_id: str, request: Request):
    data = await request.json()
    messages = data.get("messages", [])

    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)

    async def event_stream():
        try:
            async with session_factory() as db:
                # Build world book context
                result = await db.execute(
                    select(WorldBookEntry)
                    .where(WorldBookEntry.story_id == story_id)
                    .order_by(WorldBookEntry.category, WorldBookEntry.importance.desc())
                )
                entries = result.scalars().all()

                context_parts = []
                if entries:
                    for e in entries:
                        detail = f"[{e.category.value}] {e.name}"
                        if e.description:
                            detail += f": {e.description[:200]}"
                        if e.aliases:
                            detail += f" (别名: {', '.join(e.aliases)})"
                        attrs = e.attributes or {}
                        if e.category == EntryCategory.character:
                            if attrs.get("identity"):
                                detail += f" | 身份: {attrs['identity']}"
                            if attrs.get("personality"):
                                detail += f" | 性格: {', '.join(attrs['personality'])}"
                        context_parts.append(detail)

                    context_text = "\n".join(context_parts)
                    system_message = {
                        "role": "system",
                        "content": WORLD_ASSIST_SYSTEM_PROMPT + f"\n\n【当前小说的已有设定】\n{context_text}"
                    }
                else:
                    system_message = {
                        "role": "system",
                        "content": WORLD_ASSIST_SYSTEM_PROMPT + "\n\n这部小说目前还没有任何设定，请帮作者从零开始构建世界观。"
                    }

                config = await get_model_config(db, ModelRole.world_analysis)
                if not config:
                    yield "data: [ERROR] 未配置世界书分析模型，请先在设置中配置\n\n"
                    return

                provider = registry.get_or_create(config)
                full_messages = [system_message] + [{"role": m["role"], "content": m["content"]} for m in messages]

                async for chunk in provider.generate_stream(full_messages):
                    yield f"data: {chunk}\n\n"

                yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            await engine.dispose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
