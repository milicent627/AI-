import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class ForeshadowingStatus(str, enum.Enum):
    planted = "planted"
    developing = "developing"
    revealed = "revealed"
    abandoned = "abandoned"


class Foreshadowing(Base):
    __tablename__ = "foreshadowings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    plant_chapter_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reveal_chapter_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[ForeshadowingStatus] = mapped_column(SAEnum(ForeshadowingStatus), default=ForeshadowingStatus.planted)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    related_entries: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    story: Mapped["Story"] = relationship(back_populates="foreshadowings")
