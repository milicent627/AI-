from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.model_config import ModelConfig, ModelRole


async def get_model_config(db: AsyncSession, primary_role: ModelRole) -> ModelConfig | None:
    """Get model config with fallback chain: specific role → continuation → any active.
    Skips configs with empty api_key since they are not usable."""
    has_key = ModelConfig.api_key != ""

    result = await db.execute(
        select(ModelConfig)
        .where(ModelConfig.role == primary_role, ModelConfig.is_active == True, has_key)
        .limit(1)
    )
    config = result.scalar_one_or_none()
    if config:
        return config

    if primary_role != ModelRole.continuation:
        result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.role == ModelRole.continuation, ModelConfig.is_active == True, has_key)
            .limit(1)
        )
        config = result.scalar_one_or_none()
        if config:
            return config

    result = await db.execute(
        select(ModelConfig)
        .where(ModelConfig.is_active == True, has_key)
        .limit(1)
    )
    return result.scalar_one_or_none()
