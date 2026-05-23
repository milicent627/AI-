import json
import re
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.story import Chapter, Story, ChapterStatus
from ..utils.text_utils import count_chinese_words, find_chapter_split_point


class ChapterSplitService:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    async def check_and_split(self, db: AsyncSession, story_id: str, chapter_id: str) -> Chapter | None:
        """Check if chapter needs splitting and split if necessary. Returns the new chapter if split."""
        story = await db.get(Story, story_id)
        chapter = await db.get(Chapter, chapter_id)

        if not story or not chapter:
            return None

        word_count = count_chinese_words(chapter.content or "")

        if word_count < story.target_chapter_words:
            chapter.word_count = word_count
            await db.commit()
            return None

        split_index = find_chapter_split_point(chapter.content, story.target_chapter_words)

        first_part = chapter.content[:split_index].strip()
        second_part = chapter.content[split_index:].strip()

        if not first_part or len(second_part) < 100:
            chapter.word_count = word_count
            await db.commit()
            return None

        chapter.content = first_part
        chapter.word_count = count_chinese_words(first_part)
        chapter.status = ChapterStatus.archived
        chapter.is_archived = True

        archive_path = self._archive_chapter(story_id, chapter)
        chapter.archive_path = archive_path

        result = await db.execute(
            select(func.max(Chapter.chapter_number)).where(Chapter.story_id == story_id)
        )
        max_num = result.scalar() or 0

        new_chapter = Chapter(
            story_id=story_id,
            chapter_number=max_num + 1,
            title=f"第{max_num + 1}章",
            content=second_part,
            word_count=count_chinese_words(second_part),
            status=ChapterStatus.draft,
            parent_chapter_id=chapter.id,
            branch_name=chapter.branch_name,
        )
        db.add(new_chapter)

        story.current_total_words = sum(
            (await db.execute(
                select(func.sum(Chapter.word_count)).where(Chapter.story_id == story_id)
            )).scalar() or 0
        )

        await db.commit()
        return new_chapter

    def _archive_chapter(self, story_id: str, chapter: Chapter) -> str:
        archive_dir = self.data_dir / "archives" / story_id / "chapters"
        archive_dir.mkdir(parents=True, exist_ok=True)

        filename = f"ch{chapter.chapter_number:04d}_{chapter.title}.txt"
        filepath = archive_dir / filename

        content = f"第{chapter.chapter_number}章 {chapter.title}\n\n{chapter.content}"
        filepath.write_text(content, encoding="utf-8")

        return str(filepath)

    async def export_chapter(self, db: AsyncSession, chapter_id: str, fmt: str = "txt") -> str:
        chapter = await db.get(Chapter, chapter_id)
        if not chapter:
            raise ValueError("Chapter not found")

        if fmt == "txt":
            return f"第{chapter.chapter_number}章 {chapter.title}\n\n{chapter.content}"
        elif fmt == "html":
            content_html = chapter.content.replace("\n\n", "</p><p>").replace("\n", "<br>")
            return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>第{chapter.chapter_number}章 {chapter.title}</title></head>
<body><h1>第{chapter.chapter_number}章 {chapter.title}</h1><p>{content_html}</p></body></html>"""
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    async def export_full_story(self, db: AsyncSession, story_id: str, fmt: str = "txt") -> str:
        result = await db.execute(
            select(Chapter)
            .where(Chapter.story_id == story_id)
            .order_by(Chapter.chapter_number)
        )
        chapters = result.scalars().all()

        story = await db.get(Story, story_id)
        title = story.title if story else "未命名故事"

        lines = [f"《{title}》", "=" * 40, ""]
        for ch in chapters:
            lines.append(f"第{ch.chapter_number}章 {ch.title}")
            lines.append("-" * 20)
            lines.append(ch.content or "")
            lines.append("")

        return "\n".join(lines)
