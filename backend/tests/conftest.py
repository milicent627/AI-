import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base, create_engine, create_session_factory


@pytest.fixture
def temp_story_db():
    """Create a temporary story SQLite database with schema."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    engine = create_engine(path)
    import asyncio
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_setup())
    yield path
    import asyncio as _asyncio
    _asyncio.get_event_loop().run_until_complete(engine.dispose())
    os.unlink(path)


@pytest.fixture
def temp_index_db():
    """Create a temporary index SQLite database with schema."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    engine = create_engine(path)
    from app.models.prompt_preset import PromptPreset
    from app.models.prompt_fragment import PromptFragment
    from app.models.model_config import ModelConfig
    import asyncio
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_setup())
    yield path
    import asyncio as _asyncio
    _asyncio.get_event_loop().run_until_complete(engine.dispose())
    os.unlink(path)


@pytest.fixture
async def story_session(temp_story_db):
    """Async session for the story database."""
    engine = create_engine(temp_story_db)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def index_session(temp_index_db):
    """Async session for the index database."""
    engine = create_engine(temp_index_db)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()
