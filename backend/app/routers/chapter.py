from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select, func
from app.database import create_engine, create_session_factory
from app.models.story import Chapter, Story, ChapterStatus
from app.config import settings
from app.services.chapter_split import ChapterSplitService

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


def _get_db_path(story_id: str) -> str:
    return str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite")


@router.get("/{story_id}")
async def list_chapters(story_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(Chapter)
                .where(Chapter.story_id == story_id)
                .order_by(Chapter.chapter_number)
            )
            chapters = result.scalars().all()
            return {
                "chapters": [
                    {
                        "id": c.id,
                        "chapter_number": c.chapter_number,
                        "title": c.title,
                        "word_count": c.word_count,
                        "status": c.status.value if c.status else "draft",
                        "is_archived": c.is_archived,
                        "branch_name": c.branch_name,
                        "updated_at": c.updated_at.isoformat(),
                    }
                    for c in chapters
                ]
            }
    finally:
        await engine.dispose()


@router.get("/{story_id}/{chapter_id}")
async def get_chapter(story_id: str, chapter_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            chapter = await db.get(Chapter, chapter_id)
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            return {
                "id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "content": chapter.content,
                "word_count": chapter.word_count,
                "status": chapter.status.value if chapter.status else "draft",
                "is_archived": chapter.is_archived,
                "branch_name": chapter.branch_name,
                "parent_chapter_id": chapter.parent_chapter_id,
                "created_at": chapter.created_at.isoformat(),
                "updated_at": chapter.updated_at.isoformat(),
            }
    finally:
        await engine.dispose()


@router.put("/{story_id}/{chapter_id}")
async def update_chapter(story_id: str, chapter_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            chapter = await db.get(Chapter, chapter_id)
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")

            if "content" in data:
                chapter.content = data["content"]
                from app.utils.text_utils import count_chinese_words
                chapter.word_count = count_chinese_words(data["content"])
            if "title" in data:
                chapter.title = data["title"]

            await db.commit()
            return {"ok": True, "word_count": chapter.word_count}
    finally:
        await engine.dispose()


@router.post("/{story_id}/{chapter_id}/split")
async def manual_split(story_id: str, chapter_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            splitter = ChapterSplitService(settings.data_dir)
            new_chapter = await splitter.check_and_split(db, story_id, chapter_id)
            if new_chapter:
                return {"ok": True, "new_chapter_id": new_chapter.id}
            return {"ok": False, "reason": "Chapter does not meet split criteria"}
    finally:
        await engine.dispose()


@router.post("/{story_id}/branch")
async def create_branch(story_id: str, request: Request):
    data = await request.json()
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            parent_id = data["parent_chapter_id"]
            branch_name = data.get("branch_name", "分支")
            content = data.get("content", "")

            result = await db.execute(
                select(func.max(Chapter.chapter_number)).where(Chapter.story_id == story_id)
            )
            max_num = result.scalar() or 0

            new_chapter = Chapter(
                story_id=story_id,
                chapter_number=max_num + 1,
                title=f"第{max_num + 1}章",
                content=content,
                word_count=len(content),
                status=ChapterStatus.draft,
                parent_chapter_id=parent_id,
                branch_name=branch_name,
            )
            db.add(new_chapter)
            await db.commit()
            return {"ok": True, "chapter_id": new_chapter.id}
    finally:
        await engine.dispose()


@router.get("/{story_id}/export/{chapter_id}")
async def export_chapter(story_id: str, chapter_id: str, fmt: str = "txt"):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            splitter = ChapterSplitService(settings.data_dir)
            content = await splitter.export_chapter(db, chapter_id, fmt)
            media_type = "text/html" if fmt == "html" else "text/plain"
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content, media_type=media_type)
    finally:
        await engine.dispose()


@router.get("/{story_id}/export-all")
async def export_full_story(story_id: str, fmt: str = "txt"):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            splitter = ChapterSplitService(settings.data_dir)
            content = await splitter.export_full_story(db, story_id, fmt)
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
    finally:
        await engine.dispose()
