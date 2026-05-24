from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import Base, create_engine, create_session_factory
from ..models.story import Story, Chapter, ChapterStatus, PromptOrderItem
from ..config import settings
from pathlib import Path
import json

router = APIRouter(prefix="/api/stories", tags=["stories"])


def get_index_db():
    """Return the global index database session."""
    raise NotImplementedError("Use dependency injection in production")


async def get_story_db(story_id: str) -> AsyncSession:
    db_path = Path(settings.data_dir) / "archives" / story_id / "database.sqlite"
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(str(db_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    return session_factory()


@router.get("/")
async def list_stories():
    """List all stories from the data directory."""
    archives_dir = Path(settings.data_dir) / "archives"
    if not archives_dir.exists():
        return {"stories": []}

    stories = []
    for story_dir in archives_dir.iterdir():
        if story_dir.is_dir():
            db_path = story_dir / "database.sqlite"
            if db_path.exists():
                try:
                    engine = create_engine(str(db_path))
                    session_factory = create_session_factory(engine)
                    async with session_factory() as db:
                        result = await db.execute(select(Story).limit(1))
                        story = result.scalar_one_or_none()
                        if story:
                            result = await db.execute(
                                select(Chapter.chapter_number).where(
                                    Chapter.story_id == story.id
                                ).order_by(Chapter.chapter_number.desc()).limit(1)
                            )
                            last_ch = result.scalar() or 0
                            stories.append({
                                "id": story.id,
                                "title": story.title,
                                "genre": story.genre,
                                "status": story.status.value,
                                "current_total_words": story.current_total_words,
                                "chapters_count": last_ch,
                                "updated_at": story.updated_at.isoformat(),
                            })
                except Exception:
                    pass

    return {"stories": sorted(stories, key=lambda s: s["updated_at"], reverse=True)}


@router.post("/")
async def create_story(request: Request):
    """Create a new story with its own database."""
    data = await request.json()
    import uuid
    story_id = str(uuid.uuid4())
    db_path = Path(settings.data_dir) / "archives" / story_id / "database.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(str(db_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    async with session_factory() as db:
        story = Story(
            id=story_id,
            title=data.get("title", "未命名故事"),
            author=data.get("author", ""),
            genre=data.get("genre", ""),
            synopsis=data.get("synopsis", ""),
            style_guide=data.get("style_guide", ""),
            target_chapter_words=data.get("target_chapter_words", 3000),
            small_summary_chapter_count=data.get("small_summary_chapter_count", 10),
            large_summary_merge_count=data.get("large_summary_merge_count", 3),
            unsummarized_chapter_chars=data.get("unsummarized_chapter_chars", 3000),
            unsummarized_summary_chars=data.get("unsummarized_summary_chars", 3000),
            auto_hide_summarized=data.get("auto_hide_summarized", True),
            world_book_name=data.get("world_book_name", ""),
        )
        db.add(story)

        chapter = Chapter(
            story_id=story_id,
            chapter_number=1,
            title="第1章",
            content=data.get("initial_content", ""),
        )
        db.add(chapter)
        await db.commit()

        return {"id": story_id, "title": story.title, "first_chapter_id": chapter.id}


@router.get("/{story_id}")
async def get_story(story_id: str):
    """Get story details."""
    db_path = Path(settings.data_dir) / "archives" / story_id / "database.sqlite"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Story not found")

    engine = create_engine(str(db_path))
    session_factory = create_session_factory(engine)
    async with session_factory() as db:
        story = await db.get(Story, story_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        return {
            "id": story.id,
            "title": story.title,
            "author": story.author,
            "genre": story.genre,
            "synopsis": story.synopsis,
            "style_guide": story.style_guide,
            "target_chapter_words": story.target_chapter_words,
            "small_summary_chapter_count": story.small_summary_chapter_count,
            "large_summary_merge_count": story.large_summary_merge_count,
            "unsummarized_chapter_chars": story.unsummarized_chapter_chars,
            "unsummarized_summary_chars": story.unsummarized_summary_chars,
            "auto_hide_summarized": story.auto_hide_summarized,
            "current_total_words": story.current_total_words,
            "world_book_name": story.world_book_name or "",
            "status": story.status.value,
            "created_at": story.created_at.isoformat(),
            "updated_at": story.updated_at.isoformat(),
        }


@router.patch("/{story_id}")
async def update_story(story_id: str, request: Request):
    """Update story metadata."""
    data = await request.json()
    db_path = Path(settings.data_dir) / "archives" / story_id / "database.sqlite"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Story not found")

    engine = create_engine(str(db_path))
    session_factory = create_session_factory(engine)
    async with session_factory() as db:
        story = await db.get(Story, story_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        for field in ["title", "author", "genre", "synopsis", "style_guide",
                       "target_chapter_words", "small_summary_chapter_count",
                       "large_summary_merge_count", "unsummarized_chapter_chars",
                       "unsummarized_summary_chars", "auto_hide_summarized", "status",
                       "world_book_name"]:
            if field in data:
                setattr(story, field, data[field])

        await db.commit()
        return {"ok": True}


@router.delete("/{story_id}")
async def delete_story(story_id: str):
    """Delete a story and all its data."""
    import shutil
    import asyncio

    story_dir = Path(settings.data_dir) / "archives" / story_id
    if not story_dir.exists():
        raise HTTPException(status_code=404, detail="Story not found")

    # Dispose any lingering DB connections before deleting (Windows file lock)
    db_path = story_dir / "database.sqlite"
    if db_path.exists():
        engine = create_engine(str(db_path))
        await engine.dispose()

    for attempt in range(3):
        try:
            shutil.rmtree(str(story_dir))
            return {"ok": True}
        except PermissionError:
            if attempt < 2:
                await asyncio.sleep(0.5)
            else:
                raise HTTPException(status_code=500, detail="无法删除故事：文件被占用，请稍后重试")


# ── Prompt Ordering ──────────────────────────────────────────────

CONTEXT_SLOT_KEYS = ["chapter_content", "world_book_injected", "recent_summaries", "large_summary", "style_guide", "active_foreshadowings"]
FUNCTIONS = ["continuation", "polishing", "small_summary", "large_summary", "world_analysis", "foreshadowing"]


@router.get("/{story_id}/order")
async def get_order(story_id: str, function: str = "continuation"):
    """Get ordered items for a function. Each item references a fragment, world entry, or context slot."""
    engine = create_engine(
        str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite"))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(PromptOrderItem)
                .where(PromptOrderItem.story_id == story_id, PromptOrderItem.function == function)
                .order_by(PromptOrderItem.sort_order)
            )
            items = result.scalars().all()
            return {
                "items": [
                    {
                        "id": it.id,
                        "story_id": it.story_id,
                        "function": it.function,
                        "sort_order": it.sort_order,
                        "item_type": it.item_type,
                        "role": it.role,
                        "source_id": it.source_id,
                        "preset_id": it.preset_id,
                        "content_local": it.content_local,
                        "is_active": it.is_active,
                        "trigger_words": it.trigger_words,
                        "trigger_logic": it.trigger_logic,
                    }
                    for it in items
                ]
            }
    finally:
        await engine.dispose()


@router.put("/{story_id}/order")
async def save_order(story_id: str, request: Request):
    """Replace the entire ordering for a function. Body: { function, items: [...] }"""
    data = await request.json()
    func = data.get("function", "continuation")
    items = data.get("items", [])

    engine = create_engine(
        str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite"))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            # Delete existing items for this function
            existing = await db.execute(
                select(PromptOrderItem).where(
                    PromptOrderItem.story_id == story_id,
                    PromptOrderItem.function == func,
                )
            )
            for old in existing.scalars().all():
                await db.delete(old)

            # Insert new items
            for i, item_data in enumerate(items):
                it = PromptOrderItem(
                    story_id=story_id,
                    function=func,
                    sort_order=i,
                    item_type=item_data.get("item_type", "fragment"),
                    role=item_data.get("role", "system"),
                    source_id=item_data.get("source_id"),
                    preset_id=item_data.get("preset_id"),
                    content_local=item_data.get("content_local"),
                    is_active=item_data.get("is_active", True),
                    trigger_words=item_data.get("trigger_words"),
                    trigger_logic=item_data.get("trigger_logic", "any"),
                )
                db.add(it)

            await db.commit()
            return {"ok": True, "count": len(items)}
    finally:
        await engine.dispose()


@router.post("/{story_id}/order/seed")
async def seed_order(story_id: str, request: Request):
    """Auto-generate initial ordering from existing preset fragments + world entries for a function."""
    data = await request.json()
    func = data.get("function", "continuation")

    engine = create_engine(
        str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite"))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            # Check if order already exists
            existing = await db.execute(
                select(PromptOrderItem).where(
                    PromptOrderItem.story_id == story_id,
                    PromptOrderItem.function == func,
                )
            )
            if existing.scalars().first():
                return {"ok": True, "count": 0, "message": "Order already exists, skipping seed"}

            order = 10
            items_to_add = []

            # Map function to prompt preset role
            role_map = {
                "continuation": "continuation_system",
                "polishing": "polishing_system",
                "small_summary": "small_summary_user",
                "large_summary": "large_summary_user",
                "world_analysis": "world_analysis_user",
                "foreshadowing": "foreshadowing_user",
            }
            preset_role = role_map.get(func, "continuation_system")

            # Load global preset fragments
            index_engine_local = create_engine(
                str(Path(settings.data_dir) / "index.sqlite"))
            index_factory = create_session_factory(index_engine_local)
            try:
                async with index_factory() as idb:
                    from app.models.prompt_preset import PromptPreset
                    from app.models.prompt_fragment import PromptFragment
                    presets_result = await idb.execute(
                        select(PromptPreset)
                        .where(PromptPreset.role == preset_role)
                        .order_by(PromptPreset.is_default.desc())
                    )
                    for preset in presets_result.scalars().all():
                        frags_result = await idb.execute(
                            select(PromptFragment)
                            .where(PromptFragment.preset_id == preset.id)
                            .order_by(PromptFragment.sort_order)
                        )
                        for frag in frags_result.scalars().all():
                            items_to_add.append(PromptOrderItem(
                                story_id=story_id,
                                function=func,
                                sort_order=order,
                                item_type="fragment",
                                role="system" if func not in ("small_summary", "large_summary", "world_analysis", "foreshadowing") else "user",
                                source_id=frag.id,
                                preset_id=preset.id,
                                is_active=frag.is_active,
                            ))
                            order += 10

                await index_engine_local.dispose()
            except Exception:
                pass

            # Add summary / foreshadowing / style_guide items per function
            fixed_items = []
            if func == "continuation":
                fixed_items = [
                    ("style_guide", "system"),
                    ("summary", "chapter_content", "user"),
                    ("summary", "small_summaries", "user"),
                    ("summary", "large_summary", "user"),
                    ("foreshadowing", "active", "system"),
                ]
            elif func == "polishing":
                fixed_items = [
                    ("summary", "chapter_content", "user"),
                ]

            for item_def in fixed_items:
                if item_def[0] == "style_guide":
                    items_to_add.append(PromptOrderItem(
                        story_id=story_id, function=func, sort_order=order,
                        item_type="style_guide", role=item_def[1],
                        source_id="style_guide", is_active=True,
                    ))
                elif item_def[0] == "summary":
                    items_to_add.append(PromptOrderItem(
                        story_id=story_id, function=func, sort_order=order,
                        item_type="summary", role=item_def[2],
                        source_id=item_def[1], is_active=True,
                    ))
                elif item_def[0] == "foreshadowing":
                    items_to_add.append(PromptOrderItem(
                        story_id=story_id, function=func, sort_order=order,
                        item_type="foreshadowing", role=item_def[2],
                        source_id="active", is_active=True,
                    ))
                order += 10

            # Add world book entries
            from app.models.world_book import WorldBookEntry
            wb_result = await db.execute(
                select(WorldBookEntry)
                .where(WorldBookEntry.story_id == story_id, WorldBookEntry.status == "active")
                .order_by(WorldBookEntry.sort_order)
            )
            for entry in wb_result.scalars().all():
                items_to_add.append(PromptOrderItem(
                    story_id=story_id,
                    function=func,
                    sort_order=order,
                    item_type="world_entry",
                    role="user",
                    source_id=entry.id,
                    is_active=True,
                    trigger_words=[entry.name] + (entry.aliases or []),
                ))
                order += 10

            for it in items_to_add:
                db.add(it)
            await db.commit()

            return {"ok": True, "count": len(items_to_add)}
    finally:
        await engine.dispose()


@router.get("/{story_id}/order/{function}/preview")
async def preview_order(story_id: str, function: str):
    """Return the assembled prompt messages with metadata for preview."""
    from ..services.prompt_assembler import PromptAssembler

    engine = create_engine(
        str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite"))
    session_factory = create_session_factory(engine)
    index_engine = create_engine(
        str(Path(settings.data_dir) / "index.sqlite"))
    index_factory = create_session_factory(index_engine)
    try:
        async with session_factory() as db, index_factory() as idb:
            assembler = PromptAssembler()
            messages = await assembler.preview(db, idb, story_id, function)
            return {"messages": messages}
    finally:
        await engine.dispose()
        await index_engine.dispose()
