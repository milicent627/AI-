import sys
import asyncio
from pathlib import Path
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import Base, create_engine, create_session_factory
from app.models.story import Chapter
from app.providers.registry import ProviderRegistry
from app.services.continuation import ContinuationService
from app.services.chapter_split import ChapterSplitService
from app.services.world_analysis import WorldAnalysisService
from app.services.summarization import SummarizationService
from app.services.foreshadowing import ForeshadowingService
from app.services.polishing import PolishingService
from app.services.websocket_manager import ws_manager
from app.utils.text_utils import count_chinese_words
from app.config import settings

router = APIRouter(prefix="/api/continuation", tags=["continuation"])
registry = ProviderRegistry()


def _get_db_path(story_id: str) -> str:
    return str(Path(settings.data_dir) / "archives" / story_id / "database.sqlite")


async def _run_post_processing(story_id: str, chapter_id: str):
    """Run world analysis, summarization, and foreshadowing detection asynchronously."""
    try:
        engine = create_engine(_get_db_path(story_id))
        session_factory = create_session_factory(engine)
        async with session_factory() as db:
            analyzer = WorldAnalysisService(registry)
            await analyzer.analyze_chapter(db, story_id, chapter_id)

            summarizer = SummarizationService(registry)
            await summarizer.check_and_summarize(db, story_id)

            fp_service = ForeshadowingService(registry)
            await fp_service.detect_in_chapter(db, story_id, chapter_id)

        await ws_manager.notify(story_id, "analysis_complete", {
            "chapter_id": chapter_id,
        })
    except Exception as e:
        await ws_manager.notify(story_id, "analysis_error", {"error": str(e)})


@router.websocket("/ws/{story_id}")
async def websocket_endpoint(ws: WebSocket, story_id: str):
    await ws_manager.connect(story_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(story_id, ws)


def _get_index_db_path() -> str:
    return str(Path(settings.data_dir) / "index.sqlite")


@router.post("/stream")
async def continue_story_stream(request: Request):
    data = await request.json()
    story_id = data["story_id"]
    chapter_id = data["chapter_id"]

    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    index_engine = create_engine(_get_index_db_path())
    index_factory = create_session_factory(index_engine)
    service = ContinuationService(registry)

    async def event_stream():
        collected = ""
        try:
            async with session_factory() as db, index_factory() as idb:
                async for chunk in service.continue_story(
                    db, idb, story_id, chapter_id,
                    data.get("instruction", ""),
                    data.get("direction", ""),
                    data.get("branch_point", ""),
                    data.get("branch_direction", ""),
                    data.get("target_words", 800),
                ):
                    collected += chunk
                    yield f"data: {chunk}\n\n"

                chapter = await db.get(Chapter, chapter_id)
                if chapter:
                    chapter.content = (chapter.content or "") + "\n\n" + collected
                    chapter.word_count = count_chinese_words(chapter.content)
                    await db.commit()

                splitter = ChapterSplitService(settings.data_dir)
                await splitter.check_and_split(db, story_id, chapter_id)

                yield f"data: [DONE]\n\n"

            asyncio.create_task(_run_post_processing(story_id, chapter_id))

        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            await engine.dispose()
            await index_engine.dispose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/polish-stream")
async def polish_stream(request: Request):
    data = await request.json()
    story_id = data["story_id"]
    text = data["text"]
    chapter_id = data.get("chapter_id", "")

    engine = create_engine(_get_db_path(story_id))
    session_factory = create_session_factory(engine)
    index_engine = create_engine(_get_index_db_path())
    index_factory = create_session_factory(index_engine)
    polisher = PolishingService(registry)

    async def event_stream():
        collected = ""
        try:
            async with session_factory() as db, index_factory() as idb:
                async for chunk in polisher.polish_stream(db, idb, chapter_id, text):
                    collected += chunk
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"

                if chapter_id:
                    chapter = await db.get(Chapter, chapter_id)
                    if chapter:
                        chapter.content = collected
                        chapter.word_count = count_chinese_words(collected)
                        await db.commit()
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            await engine.dispose()
            await index_engine.dispose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
