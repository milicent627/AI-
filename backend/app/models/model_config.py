import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, Enum as SAEnum, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
import enum


class ProviderType(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    deepseek = "deepseek"
    ollama = "ollama"


class ModelRole(str, enum.Enum):
    continuation = "continuation"
    polishing = "polishing"
    analysis = "analysis"


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), default="")
    provider: Mapped[ProviderType] = mapped_column(SAEnum(ProviderType), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), default="")
    api_key: Mapped[str] = mapped_column(String(200), default="")
    base_url: Mapped[str] = mapped_column(String(300), default="")
    role: Mapped[ModelRole] = mapped_column(SAEnum(ModelRole), default=ModelRole.continuation)
    temperature: Mapped[float] = mapped_column(Float, default=0.8)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    extra_params: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
