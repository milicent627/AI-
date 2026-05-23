from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import Base, create_engine, create_session_factory
from ..models.story import Story, Chapter, ChapterStatus
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
                       "large_summary_merge_count", "auto_hide_summarized", "status",
                       "world_book_name"]:
            if field in data:
                setattr(story, field, data[field])

        await db.commit()
        return {"ok": True}


@router.delete("/{story_id}")
async def delete_story(story_id: str):
    """Delete a story and all its data."""
    import shutil
    story_dir = Path(settings.data_dir) / "archives" / story_id
    if story_dir.exists():
        shutil.rmtree(str(story_dir))
    return {"ok": True}
