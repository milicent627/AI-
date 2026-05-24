from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.story import Chapter, Story
from ..models.summary import Summary, SummaryType
from ..models.model_config import ModelConfig, ModelRole
from ..providers.registry import ProviderRegistry
from ..utils.prompt_templates import SUMMARY_SMALL_PROMPT, SUMMARY_LARGE_PROMPT


class SummarizationService:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    async def check_and_summarize(self, db: AsyncSession, index_db: AsyncSession, story_id: str) -> Summary | None:
        story = await db.get(Story, story_id)
        if not story:
            return None

        small_cap = max(1, story.small_summary_chapter_count)
        large_merge = max(1, story.large_summary_merge_count)

        count_result = await db.execute(
            select(func.count(Chapter.id)).where(
                Chapter.story_id == story_id,
                Chapter.is_archived == True,
            )
        )
        archived_count = count_result.scalar() or 0

        if archived_count < small_cap:
            return None

        result = await db.execute(
            select(func.count(Summary.id)).where(
                Summary.story_id == story_id,
                Summary.type == SummaryType.small,
            )
        )
        small_count = result.scalar() or 0

        expected_small = archived_count // small_cap

        if small_count < expected_small:
            return await self._generate_small_summary(db, story_id, small_count + 1, story)

        result = await db.execute(
            select(func.count(Summary.id)).where(
                Summary.story_id == story_id,
                Summary.type == SummaryType.large,
            )
        )
        large_count = result.scalar() or 0

        expected_large = (small_count // large_merge) + 1
        if small_count >= large_merge and large_count < expected_large:
            return await self._update_large_summary(db, story_id)

        return None

    async def _generate_small_summary(self, db: AsyncSession, story_id: str, level: int, story: Story = None) -> Summary | None:
        if story is None:
            story = await db.get(Story, story_id)
        if not story:
            return None

        small_cap = max(1, story.small_summary_chapter_count)
        start_chapter = (level - 1) * small_cap + 1
        end_chapter = level * small_cap

        result = await db.execute(
            select(Chapter)
            .where(
                Chapter.story_id == story_id,
                Chapter.is_archived == True,
                Chapter.chapter_number >= start_chapter,
                Chapter.chapter_number <= end_chapter,
            )
            .order_by(Chapter.chapter_number)
        )
        chapters = result.scalars().all()

        if not chapters:
            return None

        combined = "\n\n".join(c.content for c in chapters if c.content)
        word_count_before = sum(c.word_count for c in chapters)

        config = await self._get_small_summary_config(db)
        if not config:
            return None

        provider = self.registry.get_or_create(config)
        ai_result = await provider.generate([
            {"role": "user", "content": SUMMARY_SMALL_PROMPT.format(chapter_content=combined[:20000])}
        ])

        summary = Summary(
            story_id=story_id,
            type=SummaryType.small,
            level=level,
            content=ai_result.content,
            covered_chapter_ids=[c.id for c in chapters],
            word_count_before=word_count_before,
            word_count_after=len(ai_result.content),
        )
        db.add(summary)

        if story.auto_hide_summarized:
            for c in chapters:
                c.hidden = True

        await db.commit()
        return summary

    async def _update_large_summary(self, db: AsyncSession, story_id: str) -> Summary | None:
        result = await db.execute(
            select(Summary)
            .where(Summary.story_id == story_id, Summary.type == SummaryType.small)
            .order_by(Summary.level)
        )
        small_summaries = result.scalars().all()

        if not small_summaries:
            return None

        summaries_text = "\n\n---\n\n".join(s.content for s in small_summaries)

        config = await self._get_large_summary_config(db)
        if not config:
            return None

        provider = self.registry.get_or_create(config)
        result = await provider.generate([
            {"role": "user", "content": SUMMARY_LARGE_PROMPT.format(small_summaries=summaries_text[:30000])}
        ])

        summary = Summary(
            story_id=story_id,
            type=SummaryType.large,
            level=0,
            content=result.content,
            covered_chapter_ids=[c.id for c in small_summaries],
            covered_summary_ids=[s.id for s in small_summaries],
            word_count_before=sum(s.word_count_before for s in small_summaries),
            word_count_after=len(result.content),
        )
        db.add(summary)
        await db.commit()
        return summary

    async def generate_summary_manually(self, db: AsyncSession, story_id: str, summary_type: str) -> Summary | None:
        if summary_type == "small":
            result = await db.execute(
                select(func.count(Summary.id)).where(
                    Summary.story_id == story_id,
                    Summary.type == SummaryType.small,
                )
            )
            count = (result.scalar() or 0)
            return await self._generate_small_summary(db, story_id, count + 1)
        else:
            return await self._update_large_summary(db, story_id)

    async def _get_small_summary_config(self, db: AsyncSession) -> ModelConfig | None:
        from ..utils.model_fallback import get_model_config
        return await get_model_config(index_db, ModelRole.small_summary)

    async def _get_large_summary_config(self, db: AsyncSession) -> ModelConfig | None:
        from ..utils.model_fallback import get_model_config
        return await get_model_config(index_db, ModelRole.large_summary)
