import uuid
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
import httpx
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
                provider=data.get("provider", "custom"),
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


ROLE_NAMES = ["continuation", "polishing", "small_summary", "large_summary", "world_analysis", "foreshadowing"]


@router.get("/bundles")
async def list_bundles():
    """List model bundles grouped by name."""
    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(select(ModelConfig).where(ModelConfig.is_preset == False))
            configs = result.scalars().all()

            bundles: dict[str, dict] = {}
            for c in configs:
                name = c.name
                if name not in bundles:
                    bundles[name] = {"name": name, "api_key": c.api_key, "base_url": c.base_url or "", "roles": {}}
                if c.api_key and not bundles[name]["api_key"]:
                    bundles[name]["api_key"] = c.api_key
                if c.base_url and not bundles[name]["base_url"]:
                    bundles[name]["base_url"] = c.base_url
                bundles[name]["roles"][c.role.value] = {
                    "id": c.id,
                    "model_id": c.model_id,
                    "temperature": c.temperature,
                    "max_tokens": c.max_tokens,
                    "is_active": c.is_active,
                }

            return {"bundles": list(bundles.values())}
    finally:
        await engine.dispose()


@router.post("/bundle")
async def save_bundle(request: Request):
    """Save all 6 role configs as a bundle. Upserts by (name, role)."""
    data = await request.json()
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")
    roles_data = data.get("roles", {})

    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(ModelConfig).where(ModelConfig.name == name)
            )
            existing = {c.role.value: c for c in result.scalars().all()}

            for role_name in ROLE_NAMES:
                role_config = roles_data.get(role_name, {})
                if role_name in existing:
                    c = existing[role_name]
                    c.api_key = api_key
                    c.base_url = base_url
                    c.model_id = role_config.get("model_id", c.model_id)
                    c.temperature = role_config.get("temperature", c.temperature)
                    c.max_tokens = role_config.get("max_tokens", c.max_tokens)
                    c.is_active = role_config.get("is_active", c.is_active)
                else:
                    c = ModelConfig(
                        id=str(uuid.uuid4()),
                        name=name,
                        provider="custom",
                        model_id=role_config.get("model_id", ""),
                        api_key=api_key,
                        base_url=base_url,
                        role=role_name,
                        temperature=role_config.get("temperature", 0.8),
                        max_tokens=role_config.get("max_tokens", 4096),
                        is_active=role_config.get("is_active", True),
                    )
                    db.add(c)

            await db.commit()
            return {"ok": True}
    finally:
        await engine.dispose()


@router.delete("/bundle/{name}")
async def delete_bundle(name: str):
    """Delete all model configs with the given name."""
    engine = await _ensure_index_db()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(ModelConfig).where(ModelConfig.name == name)
            )
            configs = result.scalars().all()
            for c in configs:
                await db.delete(c)
            await db.commit()
            return {"ok": True, "deleted": len(configs)}
    finally:
        await engine.dispose()


@router.post("/list-provider-models")
async def list_provider_models(request: Request):
    """Fetch available models from an OpenAI-compatible API."""
    data = await request.json()
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")

    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    url = (base_url or "").rstrip("/")
    if not url:
        raise HTTPException(status_code=400, detail="base_url is required")
    url = f"{url}/v1/models"

    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Provider returned {resp.status_code}: {resp.text[:200]}",
                )
            data_resp = resp.json()
            models_raw = data_resp.get("data", [])
            models = sorted([
                m["id"] for m in models_raw
                if isinstance(m, dict) and "id" in m
            ])
        return {"models": models}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to provider timed out")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail=f"Failed to connect to {url}")
