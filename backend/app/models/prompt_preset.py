import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
import enum


class PromptRole(str, enum.Enum):
    continuation_system = "continuation_system"
    polishing_system = "polishing_system"
    small_summary_user = "small_summary_user"
    large_summary_user = "large_summary_user"
    world_analysis_user = "world_analysis_user"
    foreshadowing_user = "foreshadowing_user"
    continuation_user = "continuation_user"


class PromptPreset(Base):
    __tablename__ = "prompt_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[PromptRole] = mapped_column(SAEnum(PromptRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
