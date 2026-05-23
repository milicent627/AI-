import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class StoryStatus(str, enum.Enum):
    ongoing = "ongoing"
    completed = "completed"
    paused = "paused"


class ChapterStatus(str, enum.Enum):
    draft = "draft"
    polished = "polished"
    archived = "archived"


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), default="未命名故事")
    author: Mapped[str] = mapped_column(String(100), default="")
    genre: Mapped[str] = mapped_column(String(50), default="")
    synopsis: Mapped[str] = mapped_column(Text, default="")
    style_guide: Mapped[str] = mapped_column(Text, default="")
    target_chapter_words: Mapped[int] = mapped_column(Integer, default=3000)
    current_total_words: Mapped[int] = mapped_column(Integer, default=0)
    small_summary_chapter_count: Mapped[int] = mapped_column(Integer, default=10)
    large_summary_merge_count: Mapped[int] = mapped_column(Integer, default=3)
    auto_hide_summarized: Mapped[bool] = mapped_column(default=True)
    world_book_name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[StoryStatus] = mapped_column(SAEnum(StoryStatus), default=StoryStatus.ongoing)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    summaries: Mapped[list["Summary"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    world_entries: Mapped[list["WorldBookEntry"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    foreshadowings: Mapped[list["Foreshadowing"]] = relationship(back_populates="story", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ChapterStatus] = mapped_column(SAEnum(ChapterStatus), default=ChapterStatus.draft)
    is_archived: Mapped[bool] = mapped_column(default=False)
    archive_path: Mapped[str] = mapped_column(String(500), default="")
    parent_chapter_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    branch_name: Mapped[str] = mapped_column(String(100), default="主线")
    hidden: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    story: Mapped["Story"] = relationship(back_populates="chapters")


class PromptOrderItem(Base):
    """Per-story global prompt ordering item. Lives in each story's SQLite."""
    __tablename__ = "prompt_order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    function: Mapped[str] = mapped_column(String(50), default="continuation")  # continuation, polishing, small_summary, large_summary, world_analysis, foreshadowing
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    item_type: Mapped[str] = mapped_column(String(30), default="fragment")  # fragment | world_entry | context_slot
    role: Mapped[str] = mapped_column(String(10), default="system")  # system | user
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # fragment_id, entry_id, or slot key
    preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # only for fragment type
    content_local: Mapped[str | None] = mapped_column(Text, nullable=True)  # null = use source content
    is_active: Mapped[bool] = mapped_column(default=True)
    trigger_words: Mapped[list | None] = mapped_column(JSON, nullable=True)  # only for world_entry type
    trigger_logic: Mapped[str] = mapped_column(String(10), default="any")  # any=OR, all=AND
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContinuationRecord(Base):
    __tablename__ = "continuation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="normal")  # normal / directed / branch
    model_used: Mapped[str] = mapped_column(String(100), default="")
    prompt_used: Mapped[str] = mapped_column(Text, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    parent_record_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
