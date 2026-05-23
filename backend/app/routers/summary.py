from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from app.database import create_engine, create_session_factory
from app.models.summary import Summary, SummaryType
from app.providers.registry import ProviderRegistry
from app.services.summarization import SummarizationService
from app.config import settings

router = APIRouter(prefix="/api/summaries", tags=["summaries"])
registry = ProviderRegistry()


def _get_db_path(story_id: str) -> str:
    return str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite")


@router.get("/{story_id}")
async def list_summaries(story_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(Summary)
                .where(Summary.story_id == story_id)
                .order_by(Summary.type, Summary.level)
            )
            summaries = result.scalars().all()
            return {
                "summaries": [
                    {
                        "id": s.id,
                        "type": s.type.value,
                        "level": s.level,
                        "content": s.content,
                        "word_count_before": s.word_count_before,
                        "word_count_after": s.word_count_after,
                        "covered_chapter_ids": s.covered_chapter_ids,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in summaries
                ]
            }
    finally:
        await engine.dispose()


@router.post("/{story_id}/generate")
async def generate_summary(story_id: str, request: Request):
    data = await request.json()
    summary_type = data.get("type", "small")
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            summarizer = SummarizationService(registry)
            summary = await summarizer.generate_summary_manually(db, story_id, summary_type)
            if summary:
                return {"ok": True, "id": summary.id, "content": summary.content}
            return {"ok": False, "reason": "No chapters to summarize"}
    finally:
        await engine.dispose()


@router.delete("/{story_id}/{summary_id}")
async def delete_summary(story_id: str, summary_id: str):
    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            summary = await db.get(Summary, summary_id)
            if summary:
                await db.delete(summary)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()
