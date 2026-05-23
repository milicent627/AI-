import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from app.database import create_engine, create_session_factory
from app.models.world_book import WorldBookEntry, CharacterRelation, EntryCategory, EntryStatus
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


@router.post("/{story_id}")
async def create_entry(story_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            entry = WorldBookEntry(
                id=str(uuid.uuid4()),
                story_id=story_id,
                category=EntryCategory(data.get("category", "custom")),
                name=data.get("name", ""),
                description=data.get("description", ""),
                aliases=data.get("aliases", []),
                attributes=data.get("attributes", {}),
                importance=data.get("importance", 3),
                sort_order=data.get("sort_order", 0),
                status=EntryStatus(data.get("status", "active")),
            )
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return {
                "ok": True,
                "id": entry.id,
                "created_at": entry.created_at.isoformat(),
            }
    finally:
        await engine.dispose()


@router.post("/{story_id}/reorder")
async def reorder_entries(story_id: str, request: Request):
    data = await request.json()
    order = data.get("order", [])
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            for i, entry_id in enumerate(order):
                entry = await db.get(WorldBookEntry, entry_id)
                if entry and entry.story_id == story_id:
                    entry.sort_order = i
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


@router.get("/{story_id}/export")
async def export_world_book(story_id: str, format: str = "bookwright"):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    import json
    from fastapi.responses import Response
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(WorldBookEntry)
                .where(WorldBookEntry.story_id == story_id)
                .order_by(WorldBookEntry.sort_order, WorldBookEntry.importance.desc())
            )
            entries = result.scalars().all()

            if format == "sillytavern":
                st_entries = {}
                for i, e in enumerate(entries):
                    keys = [e.name] + (e.aliases or [])
                    st_entries[str(i)] = {
                        "uid": i,
                        "key": keys,
                        "keysecondary": [],
                        "comment": e.name,
                        "content": e.description or "",
                        "constant": False,
                        "selective": True,
                        "selectiveLogic": 0,
                        "addMemo": True,
                        "order": e.sort_order or i,
                        "position": 4,
                        "disable": e.status.value != "active" if e.status else False,
                        "ignoreBudget": False,
                        "excludeRecursion": True,
                        "preventRecursion": True,
                        "delayUntilRecursion": False,
                        "probability": 100,
                        "useProbability": True,
                        "depth": 1,
                        "group": e.category.value if e.category else "",
                        "groupOverride": False,
                        "groupWeight": 100,
                        "scanDepth": None,
                        "caseSensitive": None,
                        "matchWholeWords": None,
                        "useGroupScoring": None,
                        "automationId": "",
                        "role": 0,
                        "sticky": 0,
                        "cooldown": 0,
                        "delay": 0,
                        "triggers": [],
                        "displayIndex": i,
                    }
                export_data = {"entries": st_entries}
                filename = f"world_book_{story_id}_st.json"
            else:
                rel_result = await db.execute(
                    select(CharacterRelation)
                    .where(CharacterRelation.story_id == story_id)
                )
                relations = rel_result.scalars().all()

                export_data = {
                    "version": 1,
                    "type": "bookwright_world_book",
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "entries": [
                        {
                            "category": e.category.value,
                            "name": e.name,
                            "description": e.description,
                            "aliases": e.aliases,
                            "attributes": e.attributes,
                            "importance": e.importance,
                            "sort_order": e.sort_order,
                            "status": e.status.value if e.status else "active",
                            "version": e.version,
                        }
                        for e in entries
                    ],
                    "relations": [],
                }
                name_map = {e.id: e.name for e in entries}
                for i, r in enumerate(relations):
                    export_data["relations"].append({
                        "source_char_name": name_map.get(r.source_char_id, ""),
                        "target_char_name": name_map.get(r.target_char_id, ""),
                        "relation_type": r.relation_type,
                        "description": r.description,
                        "intensity": r.intensity,
                    })
                filename = f"world_book_{story_id}.json"

            return Response(
                content=json.dumps(export_data, ensure_ascii=False, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
    finally:
        await engine.dispose()


@router.post("/{story_id}/import")
async def import_world_book(story_id: str, file: UploadFile = File(...)):
    import json
    content = await file.read()
    try:
        import_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")

    # Detect format: SillyTavern has entries as dict (keyed by number), ours as list
    raw_entries = import_data.get("entries", None)
    is_sillytavern = isinstance(raw_entries, dict)
    is_bookwright = import_data.get("type") == "bookwright_world_book" or isinstance(raw_entries, list)

    if not is_sillytavern and not is_bookwright:
        raise HTTPException(status_code=400, detail="无法识别的世界书格式（不支持的文件）")

    # Normalize to our entry list format
    if is_sillytavern:
        normalized_entries = []
        for _, st_entry in raw_entries.items():
            keys = st_entry.get("key", [])
            name = st_entry.get("comment", keys[0] if keys else "")
            aliases = [k for k in keys if k != name] if name else keys
            category = "custom"
            group = st_entry.get("group", "")
            if group:
                for cat in EntryCategory:
                    if cat.value in group.lower():
                        category = cat.value
                        break
            normalized_entries.append({
                "name": name,
                "description": st_entry.get("content", ""),
                "aliases": aliases,
                "category": category,
                "importance": 3,
                "sort_order": st_entry.get("order", 0),
                "status": "inactive" if st_entry.get("disable", False) else "active",
                "attributes": {},
            })
        entry_list = normalized_entries
        has_relations = False
    else:
        entry_list = import_data.get("entries", [])
        has_relations = True

    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            existing_result = await db.execute(
                select(WorldBookEntry).where(WorldBookEntry.story_id == story_id)
            )
            existing_entries = existing_result.scalars().all()
            existing_index = {(e.name, e.category.value): e for e in existing_entries}

            imported_count = 0
            updated_count = 0
            new_entries = {}

            for entry_data in entry_list:
                key = (entry_data["name"], entry_data.get("category", "custom"))
                if key in existing_index:
                    e = existing_index[key]
                    updated_count += 1
                else:
                    e = WorldBookEntry(
                        id=str(uuid.uuid4()),
                        story_id=story_id,
                    )
                    db.add(e)
                    imported_count += 1

                e.category = EntryCategory(entry_data.get("category", "custom"))
                e.name = entry_data.get("name", "")
                e.description = entry_data.get("description", "")
                e.aliases = entry_data.get("aliases", [])
                e.attributes = entry_data.get("attributes", {})
                e.importance = entry_data.get("importance", 3)
                e.sort_order = entry_data.get("sort_order", 0)
                e.status = EntryStatus(entry_data.get("status", "active"))
                e.version = entry_data.get("version", 1)
                new_entries[e.name] = e

            await db.commit()

            rel_count = 0
            if has_relations:
                for rel_data in import_data.get("relations", []):
                    src = new_entries.get(rel_data.get("source_char_name", ""))
                    tgt = new_entries.get(rel_data.get("target_char_name", ""))
                    if not src:
                        src_result = await db.execute(
                            select(WorldBookEntry).where(
                                WorldBookEntry.story_id == story_id,
                                WorldBookEntry.name == rel_data.get("source_char_name", ""),
                                WorldBookEntry.category == EntryCategory.character,
                            )
                        )
                        src = src_result.scalar_one_or_none()
                    if not tgt:
                        tgt_result = await db.execute(
                            select(WorldBookEntry).where(
                                WorldBookEntry.story_id == story_id,
                                WorldBookEntry.name == rel_data.get("target_char_name", ""),
                                WorldBookEntry.category == EntryCategory.character,
                            )
                        )
                        tgt = tgt_result.scalar_one_or_none()

                    if src and tgt:
                        rel = CharacterRelation(
                            id=str(uuid.uuid4()),
                            story_id=story_id,
                            source_char_id=src.id,
                            target_char_id=tgt.id,
                            relation_type=rel_data.get("relation_type", ""),
                            description=rel_data.get("description", ""),
                            intensity=rel_data.get("intensity", 5),
                        )
                        db.add(rel)
                        rel_count += 1

            await db.commit()

            return {
                "ok": True,
                "imported": imported_count,
                "updated": updated_count,
                "relations_imported": rel_count,
            }
    finally:
        await engine.dispose()
