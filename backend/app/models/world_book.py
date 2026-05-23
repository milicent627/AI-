import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class EntryCategory(str, enum.Enum):
    character = "character"
    faction = "faction"
    location = "location"
    item = "item"
    power_system = "power_system"
    catchphrase = "catchphrase"
    custom = "custom"


class EntryStatus(str, enum.Enum):
    active = "active"
    dead = "dead"
    missing = "missing"
    inactive = "inactive"


class WorldBookEntry(Base):
    __tablename__ = "world_book_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    category: Mapped[EntryCategory] = mapped_column(SAEnum(EntryCategory), default=EntryCategory.character)
    name: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    importance: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[EntryStatus] = mapped_column(SAEnum(EntryStatus), default=EntryStatus.active)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_chapter_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    story: Mapped["Story"] = relationship(back_populates="world_entries")


class CharacterRelation(Base):
    __tablename__ = "character_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    source_char_id: Mapped[str] = mapped_column(String(36), ForeignKey("world_book_entries.id"), nullable=False)
    target_char_id: Mapped[str] = mapped_column(String(36), ForeignKey("world_book_entries.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(50), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    intensity: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
