import uuid
import json as json_module
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import Response
from sqlalchemy import select, delete as sa_delete
from app.database import Base, create_engine, create_session_factory
from app.models.prompt_preset import PromptPreset, PromptRole
from app.models.prompt_fragment import PromptFragment
from app.utils.prompt_templates import (
    DEFAULT_CONTINUATION_SYSTEM_FRAGMENTS,
    DEFAULT_POLISHING_SYSTEM_FRAGMENTS,
    CONTINUATION_USER, DIRECTED_CONTINUATION_USER,
    POLISHING_USER,
    SUMMARY_SMALL_PROMPT, SUMMARY_LARGE_PROMPT,
    WORLD_ANALYSIS_PROMPT,
    FORESHADOWING_DETECTION,
)
from app.config import settings

router = APIRouter(prefix="/api/prompt-presets", tags=["prompt_presets"])
INDEX_DB = str(Path(settings.data_dir) / "index.sqlite")

_DEFAULT_FRAGMENT_PRESETS = {
    PromptRole.continuation_system: ("续写 - 系统提示词", DEFAULT_CONTINUATION_SYSTEM_FRAGMENTS),
    PromptRole.polishing_system: ("润色 - 系统提示词", DEFAULT_POLISHING_SYSTEM_FRAGMENTS),
}

_DEFAULT_SINGLE_PRESETS = {
    PromptRole.small_summary_user: ("小总结 - 任务提示词", SUMMARY_SMALL_PROMPT),
    PromptRole.large_summary_user: ("大总结 - 任务提示词", SUMMARY_LARGE_PROMPT),
    PromptRole.world_analysis_user: ("世界书分析 - 任务提示词", WORLD_ANALYSIS_PROMPT),
    PromptRole.foreshadowing_user: ("伏笔检测 - 任务提示词", FORESHADOWING_DETECTION),
    PromptRole.continuation_user: ("续写 - 用户提示词", CONTINUATION_USER),
}


async def _ensure_db():
    engine = create_engine(INDEX_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def seed_defaults(db):
    for role, (name, fragments) in _DEFAULT_FRAGMENT_PRESETS.items():
        result = await db.execute(
            select(PromptPreset).where(PromptPreset.role == role, PromptPreset.is_default == True)
        )
        preset = result.scalar_one_or_none()
        if not preset:
            preset = PromptPreset(id=str(uuid.uuid4()), name=name, role=role, content="", is_default=True)
            db.add(preset)
            await db.flush()
            for i, text in enumerate(fragments):
                db.add(PromptFragment(preset_id=preset.id, content=text, sort_order=i, is_active=True))

    for role, (name, content) in _DEFAULT_SINGLE_PRESETS.items():
        result = await db.execute(
            select(PromptPreset).where(PromptPreset.role == role, PromptPreset.is_default == True)
        )
        if not result.scalar_one_or_none():
            preset = PromptPreset(id=str(uuid.uuid4()), name=name, role=role, content=content, is_default=True)
            db.add(preset)
            await db.flush()
            db.add(PromptFragment(preset_id=preset.id, content=content, sort_order=0, is_active=True))


def _assemble_content(fragments: list[PromptFragment]) -> str:
    active = sorted([f for f in fragments if f.is_active], key=lambda f: f.sort_order)
    return "\n\n".join(f.content for f in active)


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
            preset_result = await db.execute(query)
            presets = preset_result.scalars().all()

            result = []
            for p in presets:
                frag_result = await db.execute(
                    select(PromptFragment).where(PromptFragment.preset_id == p.id).order_by(PromptFragment.sort_order)
                )
                fragments = frag_result.scalars().all()
                result.append({
                    "id": p.id,
                    "name": p.name,
                    "role": p.role.value,
                    "content": _assemble_content(fragments) if not p.content else p.content,
                    "is_default": p.is_default,
                    "created_at": p.created_at.isoformat(),
                    "fragments": [
                        {"id": f.id, "content": f.content, "sort_order": f.sort_order, "is_active": f.is_active}
                        for f in fragments
                    ],
                })
            return {"presets": result}
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
                content="",
                is_default=False,
            )
            db.add(preset)
            await db.flush()

            fragments = data.get("fragments", [])
            for i, frag in enumerate(fragments):
                db.add(PromptFragment(
                    preset_id=preset.id,
                    content=frag.get("content", frag) if isinstance(frag, dict) else str(frag),
                    sort_order=i,
                    is_active=frag.get("is_active", True) if isinstance(frag, dict) else True,
                ))

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
            if "name" in data:
                preset.name = data["name"]
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
                await db.execute(
                    select(PromptFragment).where(PromptFragment.preset_id == preset_id)
                )
                await db.delete(preset)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.post("/{preset_id}/fragments")
async def add_fragment(preset_id: str, request: Request):
    data = await request.json()
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(PromptFragment).where(PromptFragment.preset_id == preset_id).order_by(PromptFragment.sort_order.desc()).limit(1)
            )
            last = result.scalar_one_or_none()
            next_order = (last.sort_order + 1) if last else 0

            frag = PromptFragment(
                preset_id=preset_id,
                content=data.get("content", ""),
                sort_order=data.get("sort_order", next_order),
                is_active=data.get("is_active", True),
            )
            db.add(frag)
            await db.commit()
            return {"ok": True, "id": frag.id}
    finally:
        await engine.dispose()


@router.put("/{preset_id}/fragments/{fragment_id}")
async def update_fragment(preset_id: str, fragment_id: str, request: Request):
    data = await request.json()
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            frag = await db.get(PromptFragment, fragment_id)
            if not frag or frag.preset_id != preset_id:
                raise HTTPException(status_code=404, detail="Not found")
            for field in ["content", "sort_order", "is_active"]:
                if field in data:
                    setattr(frag, field, data[field])
            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.delete("/{preset_id}/fragments/{fragment_id}")
async def delete_fragment(preset_id: str, fragment_id: str):
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            frag = await db.get(PromptFragment, fragment_id)
            if frag and frag.preset_id == preset_id:
                await db.delete(frag)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.post("/{preset_id}/reorder")
async def reorder_fragments(preset_id: str, request: Request):
    """Update sort_order for all fragments at once. Body: { "order": ["id1", "id2", ...] }"""
    data = await request.json()
    order = data.get("order", [])
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            for i, fid in enumerate(order):
                frag = await db.get(PromptFragment, fid)
                if frag and frag.preset_id == preset_id:
                    frag.sort_order = i
            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.get("/export-data")
async def export_presets(role: str = ""):
    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            await seed_defaults(db)
            await db.commit()

            query = select(PromptPreset)
            if role:
                query = query.where(PromptPreset.role == role)
            query = query.order_by(PromptPreset.role, PromptPreset.created_at.desc())
            result = await db.execute(query)
            presets = result.scalars().all()

            export_data = {
                "version": 1,
                "type": "bookwright_prompt_presets",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "presets": [],
            }

            for p in presets:
                frag_result = await db.execute(
                    select(PromptFragment).where(PromptFragment.preset_id == p.id).order_by(PromptFragment.sort_order)
                )
                fragments = frag_result.scalars().all()
                export_data["presets"].append({
                    "name": p.name,
                    "role": p.role.value,
                    "content": p.content,
                    "is_default": p.is_default,
                    "fragments": [
                        {"content": f.content, "sort_order": f.sort_order, "is_active": f.is_active}
                        for f in fragments
                    ],
                })

            return Response(
                content=json_module.dumps(export_data, ensure_ascii=False, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=prompt_presets.json"},
            )
    finally:
        await engine.dispose()


@router.post("/import-data")
async def import_presets(file: UploadFile = File(...)):
    content = await file.read()
    try:
        import_data = json_module.loads(content)
    except json_module.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")

    if import_data.get("type") != "bookwright_prompt_presets":
        raise HTTPException(status_code=400, detail="不是有效的 BookWright 提示词预设导出文件")

    engine = await _ensure_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            # Build existing index: (name, role) → preset
            existing_result = await db.execute(select(PromptPreset))
            existing_presets = existing_result.scalars().all()
            existing_index = {(p.name, p.role): p for p in existing_presets}

            imported_count = 0
            updated_count = 0

            for preset_data in import_data.get("presets", []):
                role = PromptRole(preset_data["role"])
                key = (preset_data["name"], role)
                is_default = preset_data.get("is_default", False)

                if key in existing_index and not is_default:
                    preset = existing_index[key]
                    updated_count += 1
                    # Delete old fragments
                    await db.execute(
                        sa_delete(PromptFragment).where(PromptFragment.preset_id == preset.id)
                    )
                elif key in existing_index and is_default:
                    preset = existing_index[key]
                    # Update default preset fragments
                    await db.execute(
                        sa_delete(PromptFragment).where(PromptFragment.preset_id == preset.id)
                    )
                else:
                    preset = PromptPreset(
                        id=str(uuid.uuid4()),
                        name=preset_data["name"],
                        role=role,
                        content=preset_data.get("content", ""),
                        is_default=is_default,
                    )
                    db.add(preset)
                    await db.flush()
                    imported_count += 1

                for frag_data in preset_data.get("fragments", []):
                    db.add(PromptFragment(
                        preset_id=preset.id,
                        content=frag_data.get("content", ""),
                        sort_order=frag_data.get("sort_order", 0),
                        is_active=frag_data.get("is_active", True),
                    ))

            await db.commit()
            return {
                "ok": True,
                "imported": imported_count,
                "updated": updated_count,
            }
    finally:
        await engine.dispose()
