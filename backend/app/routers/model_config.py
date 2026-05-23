import uuid
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from app.database import Base, create_engine, create_session_factory
from app.models.model_config import ModelConfig, ProviderType, ModelRole
from app.config import settings

router = APIRouter(prefix="/api/models", tags=["models"])

INDEX_DB = str(Path(settings.data_dir) / "index.sqlite")


async def _ensure_index_db():
    engine = create_engine(INDEX_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


@router.get("/")
async def list_models():
    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(select(ModelConfig))
            configs = result.scalars().all()
            return {
                "models": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "provider": c.provider.value,
                        "model_id": c.model_id,
                        "role": c.role.value,
                        "temperature": c.temperature,
                        "max_tokens": c.max_tokens,
                        "is_active": c.is_active,
                        "api_key": c.api_key[:8] + "***" if c.api_key else "",
                    }
                    for c in configs
                ]
            }
    finally:
        await engine.dispose()


@router.post("/")
async def create_model(request: Request):
    data = await request.json()
    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            config = ModelConfig(
                id=str(uuid.uuid4()),
                name=data.get("name", ""),
                provider=data.get("provider", "openai"),
                model_id=data.get("model_id", ""),
                api_key=data.get("api_key", ""),
                base_url=data.get("base_url", ""),
                role=data.get("role", "continuation"),
                temperature=data.get("temperature", 0.8),
                max_tokens=data.get("max_tokens", 4096),
                is_active=data.get("is_active", True),
            )
            db.add(config)
            await db.commit()
            return {"ok": True, "id": config.id}
    finally:
        await engine.dispose()


@router.put("/{model_id}")
async def update_model(model_id: str, request: Request):
    data = await request.json()
    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            config = await db.get(ModelConfig, model_id)
            if not config:
                raise HTTPException(status_code=404, detail="Model not found")
            for field in ["name", "provider", "model_id", "api_key", "base_url", "role",
                           "temperature", "max_tokens", "is_active"]:
                if field in data:
                    setattr(config, field, data[field])
            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            config = await db.get(ModelConfig, model_id)
            if config:
                await db.delete(config)
                await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()
