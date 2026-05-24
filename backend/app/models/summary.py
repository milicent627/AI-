import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class SummaryType(str, enum.Enum):
    small = "small"
    large = "large"


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.id"), nullable=False)
    type: Mapped[SummaryType] = mapped_column(SAEnum(SummaryType), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text, default="")
    covered_chapter_ids: Mapped[list] = mapped_column(JSON, default=list)
    covered_summary_ids: Mapped[list] = mapped_column(JSON, default=list)
    word_count_before: Mapped[int] = mapped_column(Integer, default=0)
    word_count_after: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    story: Mapped["Story"] = relationship(back_populates="summaries")
