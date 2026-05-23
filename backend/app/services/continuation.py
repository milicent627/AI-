from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.story import Story, Chapter, ContinuationRecord, ChapterStatus
from ..models.summary import Summary, SummaryType
from ..models.world_book import WorldBookEntry, EntryCategory
from ..models.foreshadowing import Foreshadowing, ForeshadowingStatus
from ..models.model_config import ModelConfig, ModelRole
from ..providers.registry import ProviderRegistry
from ..services.prompt_assembler import PromptAssembler
from ..utils.prompt_templates import (
    DIRECTED_CONTINUATION_USER,
    BRANCH_CONTINUATION_USER,
)
from ..utils.text_utils import estimate_tokens


class ContinuationService:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    async def _build_context_dict(self, db: AsyncSession, story_id: str, current_chapter_id: str) -> dict:
        """Assemble runtime context data for the PromptAssembler."""
        ctx = {}

        story = await db.get(Story, story_id)
        if story and story.style_guide:
            ctx["style_guide"] = story.style_guide

        result = await db.execute(
            select(Chapter).where(
                Chapter.story_id == story_id,
                Chapter.id == current_chapter_id,
            )
        )
        current_chapter = result.scalar_one_or_none()
        if current_chapter and current_chapter.content:
            ctx["chapter_content"] = current_chapter.content[-8000:]

        result = await db.execute(
            select(Summary)
            .where(Summary.story_id == story_id, Summary.type == SummaryType.large)
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        large_summary = result.scalar_one_or_none()
        if large_summary:
            ctx["large_summary"] = large_summary.content

        result = await db.execute(
            select(Summary)
            .where(Summary.story_id == story_id, Summary.type == SummaryType.small)
            .order_by(Summary.level.desc())
            .limit(3)
        )
        small_summaries = result.scalars().all()
        if small_summaries:
            ctx["recent_summaries"] = "\n".join(s.content for s in small_summaries)

        result = await db.execute(
            select(Foreshadowing)
            .where(
                Foreshadowing.story_id == story_id,
                Foreshadowing.status.in_([ForeshadowingStatus.planted, ForeshadowingStatus.developing]),
            )
            .order_by(Foreshadowing.priority.desc())
        )
        foreshadowings = result.scalars().all()
        if foreshadowings:
            ctx["active_foreshadowings"] = "\n".join(
                f"[{f.priority}] {f.title}: {f.description[:200]}" for f in foreshadowings
            )

        # trigger_text for world book entry matching
        if current_chapter and current_chapter.content:
            ctx["trigger_text"] = current_chapter.content[-4000:]

        return ctx

    async def continue_story(
        self,
        db: AsyncSession,
        index_db: AsyncSession,
        story_id: str,
        chapter_id: str,
        instruction: str = "",
        direction: str = "",
        branch_point: str = "",
        branch_direction: str = "",
        target_words: int = 800,
    ) -> AsyncGenerator[str, None]:
        ctx = await self._build_context_dict(db, story_id, chapter_id)

        story = await db.get(Story, story_id)
        style_guide = story.style_guide if story else ""

        assembler = PromptAssembler()
        messages = await assembler.assemble(
            db, index_db, story_id, "continuation", context=ctx
        )

        if branch_point:
            user_prompt = BRANCH_CONTINUATION_USER.format(
                context="",
                branch_point=branch_point,
                branch_direction=branch_direction,
                target_words=target_words,
            )
            cont_type = "branch"
        elif direction:
            user_prompt = DIRECTED_CONTINUATION_USER.format(
                context="",
                direction=direction,
                target_words=target_words,
                style_guide=style_guide,
            )
            cont_type = "directed"
        else:
            instruction_text = instruction or "请继续自然地续写下一段内容"
            user_prompt = instruction_text
            cont_type = "normal"

        messages.append({"role": "user", "content": user_prompt})

        from ..utils.model_fallback import get_model_config
        config = await get_model_config(db, ModelRole.continuation)
        if not config:
            raise ValueError("No continuation model configured. Please set up a model in settings.")

        provider = self.registry.get_or_create(config)

        full_response = ""
        async for chunk in provider.generate_stream(messages):
            full_response += chunk
            yield chunk

        try:
            record = ContinuationRecord(
                story_id=story_id,
                chapter_id=chapter_id,
                type=cont_type,
                model_used=config.model_id,
                prompt_used=user_prompt[:5000],
                input_tokens=estimate_tokens("\n".join(m["content"] for m in messages)),
                output_tokens=estimate_tokens(full_response),
            )
            db.add(record)
            await db.commit()
        except Exception:
            pass
