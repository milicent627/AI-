from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.story import Story, Chapter, ContinuationRecord, ChapterStatus
from ..models.summary import Summary, SummaryType
from ..models.world_book import WorldBookEntry, EntryCategory
from ..models.foreshadowing import Foreshadowing, ForeshadowingStatus
from ..models.model_config import ModelConfig, ModelRole
from ..providers.registry import ProviderRegistry
from ..utils.prompt_templates import (
    CONTINUATION_SYSTEM,
    CONTINUATION_USER,
    DIRECTED_CONTINUATION_USER,
    BRANCH_CONTINUATION_USER,
)
from ..utils.text_utils import estimate_tokens


class ContinuationService:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    async def _build_context(self, db: AsyncSession, story_id: str, current_chapter_id: str) -> str:
        """Assemble the context for continuation from multiple sources."""
        parts = []

        story = await db.get(Story, story_id)
        if story and story.style_guide:
            parts.append(f"【写作风格指南】\n{story.style_guide}")

        result = await db.execute(
            select(Chapter).where(
                Chapter.story_id == story_id,
                Chapter.id == current_chapter_id,
            )
        )
        current_chapter = result.scalar_one_or_none()
        current_text = ""
        if current_chapter and current_chapter.content:
            current_text = current_chapter.content
            parts.append(f"【当前章节正文】\n{current_text[-8000:]}")

        result = await db.execute(
            select(Chapter)
            .where(
                Chapter.story_id == story_id,
                Chapter.is_archived == True,
                Chapter.hidden == False,
            )
            .order_by(Chapter.chapter_number.desc())
            .limit(1)
        )
        last_archived = result.scalar_one_or_none()
        if last_archived and last_archived.content:
            parts.append(f"【上一章结尾】\n{last_archived.content[-3000:]}")

        result = await db.execute(
            select(Summary)
            .where(Summary.story_id == story_id, Summary.type == SummaryType.large)
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        large_summary = result.scalar_one_or_none()
        if large_summary:
            parts.append(f"【全书大总结】\n{large_summary.content}")

        result = await db.execute(
            select(Summary)
            .where(Summary.story_id == story_id, Summary.type == SummaryType.small)
            .order_by(Summary.level.desc())
            .limit(3)
        )
        small_summaries = result.scalars().all()
        if small_summaries:
            summaries_text = "\n".join(s.content for s in small_summaries)
            parts.append(f"【近期剧情摘要】\n{summaries_text}")

        result = await db.execute(
            select(WorldBookEntry)
            .where(
                WorldBookEntry.story_id == story_id,
                WorldBookEntry.importance >= 3,
            )
        )
        entries = result.scalars().all()
        if entries:
            char_entries = []
            for e in entries:
                detail = f"【{e.category.value}】{e.name}"
                if e.description:
                    detail += f"\n  {e.description[:300]}"
                if e.aliases:
                    detail += f"\n  别名: {', '.join(e.aliases)}"
                attrs = e.attributes or {}
                if e.category == EntryCategory.character:
                    if attrs.get("personality"):
                        detail += f"\n  性格: {', '.join(attrs['personality'])}"
                    if attrs.get("abilities"):
                        detail += f"\n  能力: {', '.join(attrs['abilities'])}"
                    if attrs.get("catchphrases"):
                        detail += f"\n  口头禅: {', '.join(attrs['catchphrases'])}"
                char_entries.append(detail)
            parts.append("【世界书 - 重要条目】\n" + "\n".join(char_entries))

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
            fp_text = "\n".join(
                f"  [{f.priority}] {f.title}: {f.description[:200]}" for f in foreshadowings
            )
            parts.append(f"【活跃伏笔】\n{fp_text}")

        return "\n\n".join(parts)

    async def continue_story(
        self,
        db: AsyncSession,
        story_id: str,
        chapter_id: str,
        instruction: str = "",
        direction: str = "",
        branch_point: str = "",
        branch_direction: str = "",
        target_words: int = 800,
    ) -> AsyncGenerator[str, None]:
        context = await self._build_context(db, story_id, chapter_id)

        story = await db.get(Story, story_id)
        style_guide = story.style_guide if story else ""

        if branch_point:
            user_prompt = BRANCH_CONTINUATION_USER.format(
                context=context,
                branch_point=branch_point,
                branch_direction=branch_direction,
                target_words=target_words,
            )
            cont_type = "branch"
        elif direction:
            user_prompt = DIRECTED_CONTINUATION_USER.format(
                context=context,
                direction=direction,
                target_words=target_words,
                style_guide=style_guide,
            )
            cont_type = "directed"
        else:
            instruction_text = instruction or "请继续自然地续写下一段内容"
            user_prompt = CONTINUATION_USER.format(
                context=context,
                instruction=instruction_text,
            )
            cont_type = "normal"

        messages = [
            {"role": "system", "content": CONTINUATION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

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
