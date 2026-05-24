from sqlalchemy import select
from app.models.story import PromptOrderItem, Chapter, Story
from app.models.prompt_fragment import PromptFragment
from app.models.world_book import WorldBookEntry
from app.models.summary import Summary, SummaryType
from app.models.foreshadowing import Foreshadowing, ForeshadowingStatus


class PromptAssembler:
    """Assembles prompt messages from per-story ordering configuration."""

    async def assemble(
        self, story_session, index_session, story_id: str, function: str,
        context: dict | None = None,
    ) -> list:
        """Return a list of {'role': str, 'content': str} dicts for the given story+function."""
        ctx = context or {}

        stmt = (
            select(PromptOrderItem)
            .where(
                PromptOrderItem.story_id == story_id,
                PromptOrderItem.function == function,
            )
            .order_by(PromptOrderItem.sort_order)
        )
        result = await story_session.execute(stmt)
        items = result.scalars().all()

        messages = []
        for item in items:
            if not item.is_active:
                continue
            if item.item_type == "fragment":
                content = await self._resolve_fragment(index_session, item.source_id)
                if content is None:
                    continue
                messages.append({"role": item.role, "content": content})
            elif item.item_type == "world_entry":
                content = await self._resolve_world_entry(
                    story_session, item, ctx
                )
                if content is None:
                    continue
                messages.append({"role": item.role, "content": content})
            elif item.item_type == "summary":
                content = await self._resolve_summary(
                    story_session, story_id, item.source_id
                )
                if content is None:
                    continue
                messages.append({"role": item.role, "content": content})
            elif item.item_type == "foreshadowing":
                content = await self._resolve_foreshadowing(
                    story_session, story_id
                )
                if content is None:
                    continue
                messages.append({"role": item.role, "content": content})
            elif item.item_type == "style_guide":
                content = await self._resolve_style_guide(
                    story_session, story_id
                )
                if content is None:
                    continue
                messages.append({"role": item.role, "content": content})

        return messages

    async def _resolve_fragment(self, index_session, source_id: str) -> str | None:
        stmt = select(PromptFragment).where(PromptFragment.id == source_id)
        result = await index_session.execute(stmt)
        fragment = result.scalar_one_or_none()
        if fragment is None:
            return None
        return fragment.content

    async def _resolve_world_entry(self, story_session, item, ctx: dict) -> str | None:
        stmt = select(WorldBookEntry).where(WorldBookEntry.id == item.source_id)
        result = await story_session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None:
            return None

        if item.trigger_words and len(item.trigger_words) > 0:
            text = ctx.get("trigger_text", "")
            if not self._match_triggers(item.trigger_words, item.trigger_logic, text):
                return None

        return f"{entry.name}: {entry.description}"

    async def _resolve_summary(self, story_session, story_id: str, source_id: str) -> str | None:
        if source_id == "chapter_content":
            return await self._get_chapter_content(story_session, story_id)
        elif source_id == "small_summaries":
            return await self._get_small_summaries(story_session, story_id)
        elif source_id == "large_summary":
            return await self._get_large_summary(story_session, story_id)
        return None

    async def _get_chapter_content(self, story_session, story_id: str) -> str | None:
        # Get all covered chapter IDs from small summaries
        small_result = await story_session.execute(
            select(Summary).where(
                Summary.story_id == story_id,
                Summary.type == SummaryType.small,
            )
        )
        covered_ids = set()
        for s in small_result.scalars().all():
            for cid in (s.covered_chapter_ids or []):
                covered_ids.add(cid)

        # Get non-archived chapters that are not covered by any summary
        chapters_result = await story_session.execute(
            select(Chapter)
            .where(
                Chapter.story_id == story_id,
                Chapter.id.notin_(covered_ids) if covered_ids else True,
                Chapter.is_archived == False,
            )
            .order_by(Chapter.chapter_number)
        )
        chapters = chapters_result.scalars().all()
        if not chapters:
            return None

        return "\n\n".join(c.content for c in chapters if c.content)

    async def _get_small_summaries(self, story_session, story_id: str) -> str | None:
        # Get all covered summary IDs from large summaries
        large_result = await story_session.execute(
            select(Summary).where(
                Summary.story_id == story_id,
                Summary.type == SummaryType.large,
            )
        )
        covered_ids = set()
        for ls in large_result.scalars().all():
            for sid in (ls.covered_summary_ids or []):
                covered_ids.add(sid)

        # Get small summaries not covered by large summaries
        stmt = select(Summary).where(
            Summary.story_id == story_id,
            Summary.type == SummaryType.small,
        )
        if covered_ids:
            stmt = stmt.where(Summary.id.notin_(covered_ids))
        stmt = stmt.order_by(Summary.level)

        result = await story_session.execute(stmt)
        summaries = result.scalars().all()
        if not summaries:
            return None

        return "\n\n".join(s.content for s in summaries)

    async def _get_large_summary(self, story_session, story_id: str) -> str | None:
        result = await story_session.execute(
            select(Summary)
            .where(
                Summary.story_id == story_id,
                Summary.type == SummaryType.large,
            )
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        summary = result.scalar_one_or_none()
        if summary is None:
            return None
        return summary.content

    async def _resolve_foreshadowing(self, story_session, story_id: str) -> str | None:
        result = await story_session.execute(
            select(Foreshadowing)
            .where(
                Foreshadowing.story_id == story_id,
                Foreshadowing.status.in_([
                    ForeshadowingStatus.planted,
                    ForeshadowingStatus.developing,
                ]),
            )
            .order_by(Foreshadowing.priority.desc())
        )
        items = result.scalars().all()
        if not items:
            return None

        return "\n".join(
            f"[{f.priority}] {f.title}: {f.description[:200]}" for f in items
        )

    async def _resolve_style_guide(self, story_session, story_id: str) -> str | None:
        result = await story_session.execute(
            select(Story.style_guide).where(Story.id == story_id)
        )
        style_guide = result.scalar_one_or_none()
        if not style_guide:
            return None
        return style_guide

    def _match_triggers(self, trigger_words: list, logic: str, text: str) -> bool:
        if logic == "all":
            return all(w in text for w in trigger_words)
        return any(w in text for w in trigger_words)

    async def preview(
        self, story_session, index_session, story_id: str, function: str,
    ) -> list:
        """Return assembled messages with name/type metadata for preview display."""
        from app.models.prompt_fragment import PromptFragment

        stmt = (
            select(PromptOrderItem)
            .where(
                PromptOrderItem.story_id == story_id,
                PromptOrderItem.function == function,
            )
            .order_by(PromptOrderItem.sort_order)
        )
        result = await story_session.execute(stmt)
        items = result.scalars().all()

        messages = []
        for item in items:
            if not item.is_active:
                continue

            name = item.source_id
            if item.item_type == "fragment":
                content = await self._resolve_fragment(index_session, item.source_id)
                if content is None:
                    continue
                # Try to get fragment name from the preset
                frag_result = await index_session.execute(
                    select(PromptFragment).where(PromptFragment.id == item.source_id)
                )
                frag = frag_result.scalar_one_or_none()
                name = frag.preset_id if frag else item.source_id
            elif item.item_type == "world_entry":
                entry_result = await story_session.execute(
                    select(WorldBookEntry).where(WorldBookEntry.id == item.source_id)
                )
                entry = entry_result.scalar_one_or_none()
                if entry is None:
                    continue
                content = f"{entry.name}: {entry.description}"
                name = entry.name
            elif item.item_type == "summary":
                content = await self._resolve_summary(story_session, story_id, item.source_id)
                if content is None:
                    continue
                name = "摘要" if item.source_id == "small_summaries" else "大摘要"
            elif item.item_type == "foreshadowing":
                content = await self._resolve_foreshadowing(story_session, story_id)
                if content is None:
                    continue
                name = "伏笔列表"
            elif item.item_type == "style_guide":
                content = await self._resolve_style_guide(story_session, story_id)
                if content is None:
                    continue
                name = "风格指南"
            else:
                continue

            messages.append({
                "role": item.role,
                "name": name,
                "item_type": item.item_type,
                "content": content,
            })

        return messages
