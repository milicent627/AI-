from sqlalchemy import select
from app.models.story import PromptOrderItem
from app.models.prompt_fragment import PromptFragment
from app.models.world_book import WorldBookEntry


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
            elif item.item_type == "context_slot":
                content = ctx.get(item.source_id, item.content_local or "")
                messages.append({"role": item.role, "content": content})
            elif item.item_type == "world_entry":
                content = await self._resolve_world_entry(
                    story_session, item, ctx
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

    def _match_triggers(self, trigger_words: list, logic: str, text: str) -> bool:
        if logic == "all":
            return all(w in text for w in trigger_words)
        return any(w in text for w in trigger_words)
