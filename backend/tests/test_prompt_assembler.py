import pytest
import uuid
from app.services.prompt_assembler import PromptAssembler
from app.models.prompt_preset import PromptPreset, PromptRole
from app.models.prompt_fragment import PromptFragment
from app.models.story import PromptOrderItem
from app.models.world_book import WorldBookEntry, EntryCategory, EntryStatus


class TestEmptyOrder:
    """Slice 1: Empty order returns empty messages."""

    @pytest.mark.asyncio
    async def test_empty_order_returns_empty_messages(self, story_session, index_session):
        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation"
        )
        assert result == []


class TestFragmentsResolved:
    """Slice 2: Active fragment items resolve content from index DB."""

    @pytest.mark.asyncio
    async def test_active_fragment_resolves_content(self, story_session, index_session):
        preset_id = str(uuid.uuid4())
        fragment_id = str(uuid.uuid4())
        order_item_id = str(uuid.uuid4())

        preset = PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        )
        fragment = PromptFragment(
            id=fragment_id, preset_id=preset_id,
            content="你是一位小说家。", sort_order=0, is_active=True
        )
        order_item = PromptOrderItem(
            id=order_item_id, story_id="test-story-id",
            function="continuation", sort_order=1,
            item_type="fragment", role="system",
            source_id=fragment_id, preset_id=preset_id, is_active=True
        )

        index_session.add_all([preset, fragment])
        story_session.add(order_item)
        await index_session.commit()
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation"
        )

        assert len(result) == 1
        assert result[0] == {"role": "system", "content": "你是一位小说家。"}

    @pytest.mark.asyncio
    async def test_inactive_fragment_excluded(self, story_session, index_session):
        preset_id = str(uuid.uuid4())
        active_id = str(uuid.uuid4())
        inactive_id = str(uuid.uuid4())
        order1_id = str(uuid.uuid4())
        order2_id = str(uuid.uuid4())

        preset = PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        )
        active_frag = PromptFragment(
            id=active_id, preset_id=preset_id,
            content="active fragment", sort_order=0, is_active=True
        )
        inactive_frag = PromptFragment(
            id=inactive_id, preset_id=preset_id,
            content="inactive fragment", sort_order=1, is_active=True
        )

        index_session.add_all([preset, active_frag, inactive_frag])
        await index_session.commit()

        order1 = PromptOrderItem(
            id=order1_id, story_id="test-story-id",
            function="continuation", sort_order=1,
            item_type="fragment", role="system",
            source_id=active_id, preset_id=preset_id, is_active=True
        )
        order2 = PromptOrderItem(
            id=order2_id, story_id="test-story-id",
            function="continuation", sort_order=2,
            item_type="fragment", role="system",
            source_id=inactive_id, preset_id=preset_id, is_active=False
        )
        story_session.add_all([order1, order2])
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation"
        )

        assert len(result) == 1
        assert result[0]["content"] == "active fragment"

    @pytest.mark.asyncio
    async def test_items_respect_sort_order(self, story_session, index_session):
        preset_id = str(uuid.uuid4())
        frag_ids = [str(uuid.uuid4()) for _ in range(3)]
        order_ids = [str(uuid.uuid4()) for _ in range(3)]

        preset = PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        )
        index_session.add(preset)

        contents = ["first", "second", "third"]
        for i, (fid, c) in enumerate(zip(frag_ids, contents)):
            index_session.add(PromptFragment(
                id=fid, preset_id=preset_id, content=c,
                sort_order=i, is_active=True
            ))

        # Insert with non-sequential sort_order to verify ordering
        orders = [
            (order_ids[0], frag_ids[2], 3),  # "third" at position 3
            (order_ids[1], frag_ids[0], 1),  # "first" at position 1
            (order_ids[2], frag_ids[1], 2),  # "second" at position 2
        ]
        for oid, fid, so in orders:
            story_session.add(PromptOrderItem(
                id=oid, story_id="test-story-id",
                function="continuation", sort_order=so,
                item_type="fragment", role="system",
                source_id=fid, preset_id=preset_id, is_active=True
            ))

        await index_session.commit()
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation"
        )

        assert len(result) == 3
        assert [m["content"] for m in result] == ["first", "second", "third"]


class TestContextSlots:
    """Slice 4: Context slot items resolve from context dict."""

    @pytest.mark.asyncio
    async def test_context_slot_resolves_content(self, story_session, index_session):
        order_item_id = str(uuid.uuid4())
        order_item = PromptOrderItem(
            id=order_item_id, story_id="test-story-id",
            function="continuation", sort_order=1,
            item_type="context_slot", role="user",
            source_id="chapter_content", is_active=True
        )
        story_session.add(order_item)
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation",
            context={"chapter_content": "张三推开门走进了房间。"}
        )

        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "张三推开门走进了房间。"}


class TestWorldEntries:
    """Slice 5: World entry items resolve and match triggers."""

    @pytest.mark.asyncio
    async def test_world_entry_with_trigger_match(self, story_session, index_session):
        entry_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())

        entry = WorldBookEntry(
            id=entry_id, story_id="test-story-id",
            category=EntryCategory.character, name="张三",
            description="主角，25岁青年。", status=EntryStatus.active, sort_order=0
        )
        order_item = PromptOrderItem(
            id=order_id, story_id="test-story-id",
            function="continuation", sort_order=1,
            item_type="world_entry", role="system",
            source_id=entry_id, is_active=True,
            trigger_words=["张三"], trigger_logic="any"
        )
        story_session.add_all([entry, order_item])
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation",
            context={"trigger_text": "张三推开门走进了房间。"}
        )

        assert len(result) == 1
        assert result[0]["role"] == "system"
        assert "张三" in result[0]["content"]
        assert "25岁青年" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_world_entry_no_trigger_match_excluded(self, story_session, index_session):
        entry_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())

        entry = WorldBookEntry(
            id=entry_id, story_id="test-story-id",
            category=EntryCategory.character, name="张三",
            description="主角。", status=EntryStatus.active, sort_order=0
        )
        order_item = PromptOrderItem(
            id=order_id, story_id="test-story-id",
            function="continuation", sort_order=1,
            item_type="world_entry", role="system",
            source_id=entry_id, is_active=True,
            trigger_words=["张三"], trigger_logic="any"
        )
        story_session.add_all([entry, order_item])
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation",
            context={"trigger_text": "李四推开门走进了房间。"}
        )

        assert len(result) == 0


class TestRoleSeparation:
    """Slice 7: System and user roles preserved in assembled messages."""

    @pytest.mark.asyncio
    async def test_mixed_roles_preserved(self, story_session, index_session):
        preset_id = str(uuid.uuid4())
        frag_id = str(uuid.uuid4())
        order1_id = str(uuid.uuid4())
        order2_id = str(uuid.uuid4())
        order3_id = str(uuid.uuid4())

        preset = PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        )
        fragment = PromptFragment(
            id=frag_id, preset_id=preset_id,
            content="system instruction", sort_order=0, is_active=True
        )
        index_session.add_all([preset, fragment])
        await index_session.commit()

        order1 = PromptOrderItem(
            id=order1_id, story_id="test-story-id",
            function="continuation", sort_order=1,
            item_type="fragment", role="system",
            source_id=frag_id, preset_id=preset_id, is_active=True
        )
        order2 = PromptOrderItem(
            id=order2_id, story_id="test-story-id",
            function="continuation", sort_order=2,
            item_type="context_slot", role="user",
            source_id="chapter_content", is_active=True,
            content_local="user content"
        )
        order3 = PromptOrderItem(
            id=order3_id, story_id="test-story-id",
            function="continuation", sort_order=3,
            item_type="context_slot", role="user",
            source_id="summaries", is_active=True,
            content_local="summary content"
        )
        story_session.add_all([order1, order2, order3])
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, "test-story-id", "continuation",
            context={"chapter_content": "user content", "summaries": "summary content"}
        )

        assert len(result) == 3
        assert result[0] == {"role": "system", "content": "system instruction"}
        assert result[1] == {"role": "user", "content": "user content"}
        assert result[2] == {"role": "user", "content": "summary content"}


class TestFullIntegration:
    """Slice 8: All item types combined in a single assembly."""

    @pytest.mark.asyncio
    async def test_mixed_items_full_pipeline(self, story_session, index_session):
        story_id = "test-story-id"
        func = "continuation"

        preset_id = str(uuid.uuid4())
        frag1_id = str(uuid.uuid4())
        frag2_id = str(uuid.uuid4())
        entry_id = str(uuid.uuid4())
        oid1 = str(uuid.uuid4())  # system fragment (active)
        oid2 = str(uuid.uuid4())  # user context slot
        oid3 = str(uuid.uuid4())  # world entry (active, with trigger match)
        oid4 = str(uuid.uuid4())  # user fragment (active)
        oid5 = str(uuid.uuid4())  # inactive system fragment (should be excluded)

        preset = PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        )
        frag1 = PromptFragment(
            id=frag1_id, preset_id=preset_id,
            content="You are a novelist.", sort_order=0, is_active=True
        )
        frag2 = PromptFragment(
            id=frag2_id, preset_id=preset_id,
            content="Write the next paragraph.", sort_order=1, is_active=True
        )
        index_session.add_all([preset, frag1, frag2])
        await index_session.commit()

        entry = WorldBookEntry(
            id=entry_id, story_id=story_id,
            category=EntryCategory.location, name="Beijing",
            description="Capital city.", status=EntryStatus.active, sort_order=0
        )

        # Order: system fragment, user slot, world entry, user fragment, inactive system fragment
        order1 = PromptOrderItem(
            id=oid1, story_id=story_id, function=func, sort_order=1,
            item_type="fragment", role="system",
            source_id=frag1_id, preset_id=preset_id, is_active=True
        )
        order2 = PromptOrderItem(
            id=oid2, story_id=story_id, function=func, sort_order=2,
            item_type="context_slot", role="user",
            source_id="chapter_content", is_active=True,
            content_local="{章节正文}"
        )
        order3 = PromptOrderItem(
            id=oid3, story_id=story_id, function=func, sort_order=3,
            item_type="world_entry", role="system",
            source_id=entry_id, is_active=True,
            trigger_words=["Beijing"], trigger_logic="any"
        )
        order4 = PromptOrderItem(
            id=oid4, story_id=story_id, function=func, sort_order=4,
            item_type="fragment", role="user",
            source_id=frag2_id, preset_id=preset_id, is_active=True
        )
        order5 = PromptOrderItem(
            id=oid5, story_id=story_id, function=func, sort_order=5,
            item_type="fragment", role="system",
            source_id=frag1_id, preset_id=preset_id, is_active=False
        )
        story_session.add_all([entry, order1, order2, order3, order4, order5])
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, func,
            context={
                "chapter_content": "They arrived in Beijing.",
                "trigger_text": "They arrived in Beijing.",
            }
        )

        # 5 items, but 1 is inactive → 4 messages
        assert len(result) == 4

        assert result[0] == {"role": "system", "content": "You are a novelist."}
        assert result[1] == {"role": "user", "content": "They arrived in Beijing."}
        assert result[2] == {"role": "system", "content": "Beijing: Capital city."}
        assert result[3] == {"role": "user", "content": "Write the next paragraph."}
