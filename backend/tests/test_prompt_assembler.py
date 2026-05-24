import pytest
import uuid
from app.services.prompt_assembler import PromptAssembler
from app.models.prompt_preset import PromptPreset, PromptRole
from app.models.prompt_fragment import PromptFragment
from app.models.story import PromptOrderItem, Chapter, ChapterStatus, Story, StoryStatus
from app.models.world_book import WorldBookEntry, EntryCategory, EntryStatus
from app.models.summary import Summary, SummaryType
from app.models.foreshadowing import Foreshadowing, ForeshadowingStatus


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

        preset = PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        )
        fragment = PromptFragment(
            id=fragment_id, preset_id=preset_id,
            content="你是一位小说家。", sort_order=0, is_active=True
        )
        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id="test-story-id",
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

        story_session.add_all([
            PromptOrderItem(id=str(uuid.uuid4()), story_id="test-story-id",
                function="continuation", sort_order=1,
                item_type="fragment", role="system",
                source_id=active_id, preset_id=preset_id, is_active=True),
            PromptOrderItem(id=str(uuid.uuid4()), story_id="test-story-id",
                function="continuation", sort_order=2,
                item_type="fragment", role="system",
                source_id=inactive_id, preset_id=preset_id, is_active=False),
        ])
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

        index_session.add(PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        ))

        contents = ["first", "second", "third"]
        for fid, c in zip(frag_ids, contents):
            index_session.add(PromptFragment(
                id=fid, preset_id=preset_id, content=c,
                sort_order=0, is_active=True
            ))

        orders = [
            (frag_ids[2], 3),
            (frag_ids[0], 1),
            (frag_ids[1], 2),
        ]
        for fid, so in orders:
            story_session.add(PromptOrderItem(
                id=str(uuid.uuid4()), story_id="test-story-id",
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


class TestSummaryItems:
    """Slice 4: Summary items resolve with cascade skipping."""

    @pytest.mark.asyncio
    async def test_chapter_content_returns_uncovered_chapters(self, story_session, index_session):
        story_id = "test-story-id"

        # Chapters 1-2 are covered by a small summary, chapter 3 is not
        story_session.add(Story(id=story_id, title="test"))
        ch1 = Chapter(id=str(uuid.uuid4()), story_id=story_id, chapter_number=1,
                       content="第一章内容", status=ChapterStatus.archived, is_archived=True)
        ch2 = Chapter(id=str(uuid.uuid4()), story_id=story_id, chapter_number=2,
                       content="第二章内容", status=ChapterStatus.archived, is_archived=True)
        ch3 = Chapter(id=str(uuid.uuid4()), story_id=story_id, chapter_number=3,
                       content="第三章内容", status=ChapterStatus.draft, is_archived=False)
        story_session.add_all([ch1, ch2, ch3])

        # Small summary covers chapters 1-2
        story_session.add(Summary(
            id=str(uuid.uuid4()), story_id=story_id, type=SummaryType.small, level=1,
            content="小总结", covered_chapter_ids=[ch1.id, ch2.id]
        ))
        await story_session.commit()

        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id=story_id,
            function="continuation", sort_order=1,
            item_type="summary", role="user",
            source_id="chapter_content", is_active=True
        )
        story_session.add(order_item)
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, "continuation"
        )

        # Only chapter 3 should be in the result (not covered by any summary)
        assert len(result) == 1
        assert "第三章内容" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_small_summaries_excludes_covered_by_large(self, story_session, index_session):
        story_id = "test-story-id"
        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())

        story_session.add(Story(id=story_id, title="test"))
        story_session.add(Summary(
            id=sid1, story_id=story_id, type=SummaryType.small, level=1,
            content="小总结1", covered_summary_ids=[]
        ))
        story_session.add(Summary(
            id=sid2, story_id=story_id, type=SummaryType.small, level=2,
            content="小总结2", covered_summary_ids=[]
        ))
        # Large summary covers small summary 1
        story_session.add(Summary(
            id=str(uuid.uuid4()), story_id=story_id, type=SummaryType.large, level=0,
            content="大总结", covered_summary_ids=[sid1]
        ))
        await story_session.commit()

        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id=story_id,
            function="continuation", sort_order=1,
            item_type="summary", role="user",
            source_id="small_summaries", is_active=True
        )
        story_session.add(order_item)
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, "continuation"
        )

        # Only small summary 2 should appear (1 is covered by large)
        assert len(result) == 1
        assert "小总结2" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_large_summary_returns_latest(self, story_session, index_session):
        story_id = "test-story-id"

        story_session.add(Story(id=story_id, title="test"))
        story_session.add(Summary(
            id=str(uuid.uuid4()), story_id=story_id, type=SummaryType.large, level=0,
            content="大总结内容", covered_summary_ids=[]
        ))
        await story_session.commit()

        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id=story_id,
            function="continuation", sort_order=1,
            item_type="summary", role="system",
            source_id="large_summary", is_active=True
        )
        story_session.add(order_item)
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, "continuation"
        )

        assert len(result) == 1
        assert "大总结内容" in result[0]["content"]


class TestWorldEntries:
    """Slice 5: World entry items resolve and match triggers."""

    @pytest.mark.asyncio
    async def test_world_entry_with_trigger_match(self, story_session, index_session):
        entry_id = str(uuid.uuid4())

        entry = WorldBookEntry(
            id=entry_id, story_id="test-story-id",
            category=EntryCategory.character, name="张三",
            description="主角，25岁青年。", status=EntryStatus.active, sort_order=0
        )
        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id="test-story-id",
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

        entry = WorldBookEntry(
            id=entry_id, story_id="test-story-id",
            category=EntryCategory.character, name="张三",
            description="主角。", status=EntryStatus.active, sort_order=0
        )
        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id="test-story-id",
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


class TestForeshadowing:
    """Slice 6: Foreshadowing items resolve from story DB."""

    @pytest.mark.asyncio
    async def test_active_foreshadowings_resolved(self, story_session, index_session):
        story_id = "test-story-id"

        story_session.add(Story(id=story_id, title="test"))
        story_session.add(Foreshadowing(
            id=str(uuid.uuid4()), story_id=story_id,
            title="神秘黑衣人", description="第三章出现的神秘人物尚未揭示身份",
            status=ForeshadowingStatus.planted, priority=5
        ))
        story_session.add(Foreshadowing(
            id=str(uuid.uuid4()), story_id=story_id,
            title="已揭示伏笔", description="这个已经揭示",
            status=ForeshadowingStatus.revealed, priority=3
        ))
        await story_session.commit()

        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id=story_id,
            function="continuation", sort_order=1,
            item_type="foreshadowing", role="system",
            source_id="active", is_active=True
        )
        story_session.add(order_item)
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, "continuation"
        )

        assert len(result) == 1
        assert "神秘黑衣人" in result[0]["content"]
        assert "已揭示" not in result[0]["content"]


class TestStyleGuide:
    """Slice 7: Style guide item resolves from Story."""

    @pytest.mark.asyncio
    async def test_style_guide_resolved(self, story_session, index_session):
        story_id = "test-story-id"

        story_session.add(Story(id=story_id, title="test", style_guide="使用古风语言，对话用文言文"))
        await story_session.commit()

        order_item = PromptOrderItem(
            id=str(uuid.uuid4()), story_id=story_id,
            function="continuation", sort_order=1,
            item_type="style_guide", role="system",
            source_id="style_guide", is_active=True
        )
        story_session.add(order_item)
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, "continuation"
        )

        assert len(result) == 1
        assert "古风" in result[0]["content"]


class TestFullIntegration:
    """Slice 8: All item types combined."""

    @pytest.mark.asyncio
    async def test_mixed_items_full_pipeline(self, story_session, index_session):
        story_id = "test-story-id"
        func = "continuation"

        # Index DB: preset + fragments
        preset_id = str(uuid.uuid4())
        frag1_id = str(uuid.uuid4())
        frag2_id = str(uuid.uuid4())

        index_session.add(PromptPreset(
            id=preset_id, name="test-preset",
            role=PromptRole.continuation_system, content="fallback"
        ))
        index_session.add(PromptFragment(
            id=frag1_id, preset_id=preset_id,
            content="You are a novelist.", sort_order=0, is_active=True
        ))
        index_session.add(PromptFragment(
            id=frag2_id, preset_id=preset_id,
            content="Write the next paragraph.", sort_order=1, is_active=True
        ))
        await index_session.commit()

        # Story DB: story, chapter, world entry, summary, foreshadowing
        story_session.add(Story(id=story_id, title="test", style_guide="Use vivid descriptions."))
        ch1 = Chapter(id=str(uuid.uuid4()), story_id=story_id, chapter_number=1,
                       content="第一章内容", status=ChapterStatus.draft, is_archived=False)
        story_session.add(ch1)
        wb_entry_id = str(uuid.uuid4())
        story_session.add(WorldBookEntry(
            id=wb_entry_id, story_id=story_id,
            category=EntryCategory.location, name="Beijing",
            description="Capital city.", status=EntryStatus.active, sort_order=0
        ))
        summary_id = str(uuid.uuid4())
        story_session.add(Summary(
            id=summary_id, story_id=story_id, type=SummaryType.small, level=1,
            content="前情摘要内容", covered_chapter_ids=[]
        ))
        story_session.add(Foreshadowing(
            id=str(uuid.uuid4()), story_id=story_id,
            title="神秘信", description="一封来历不明的信",
            status=ForeshadowingStatus.planted, priority=4
        ))

        # Order items: fragment (system), chapter_content (user), world_entry (system),
        # small_summaries (user), foreshadowing (system), fragment (user), style_guide (system, inactive)
        story_session.add_all([
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=1, item_type="fragment", role="system",
                source_id=frag1_id, preset_id=preset_id, is_active=True),
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=2, item_type="summary", role="user",
                source_id="chapter_content", is_active=True),
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=3, item_type="world_entry", role="system",
                source_id=wb_entry_id, is_active=True,
                trigger_words=["Beijing"], trigger_logic="any"),
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=4, item_type="summary", role="user",
                source_id="small_summaries", is_active=True),
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=5, item_type="foreshadowing", role="system",
                source_id="active", is_active=True),
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=6, item_type="fragment", role="user",
                source_id=frag2_id, preset_id=preset_id, is_active=True),
            PromptOrderItem(id=str(uuid.uuid4()), story_id=story_id, function=func,
                sort_order=7, item_type="style_guide", role="system",
                source_id="style_guide", is_active=False),
        ])
        await story_session.commit()

        assembler = PromptAssembler()
        result = await assembler.assemble(
            story_session, index_session, story_id, func,
            context={"trigger_text": "They arrived in Beijing."}
        )

        # 7 items, 1 inactive → 6 messages
        assert len(result) == 6

        assert result[0] == {"role": "system", "content": "You are a novelist."}
        assert "第一章内容" in result[1]["content"]
        assert result[1]["role"] == "user"
        assert "Beijing" in result[2]["content"]
        assert result[2]["role"] == "system"
        assert "前情摘要内容" in result[3]["content"]
        assert result[3]["role"] == "user"
        assert "神秘信" in result[4]["content"]
        assert result[4]["role"] == "system"
        assert result[5] == {"role": "user", "content": "Write the next paragraph."}
