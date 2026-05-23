from sqlalchemy.ext.asyncio import AsyncSession
from ..models.story import Chapter, ChapterStatus
from ..models.model_config import ModelConfig, ModelRole
from ..providers.registry import ProviderRegistry
from ..utils.prompt_templates import POLISHING_SYSTEM, POLISHING_USER


class PolishingService:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    async def polish_chapter(self, db: AsyncSession, chapter_id: str, full_chapter: bool = False) -> tuple[str, str]:
        """Polish chapter content. Returns (original_text, polished_text)."""
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or not chapter.content:
            raise ValueError("Chapter not found or empty")

        config_result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.role == ModelRole.polishing, ModelConfig.is_active == True)
            .limit(1)
        )
        config = config_result.scalar_one_or_none()
        if not config:
            result = await db.execute(
                select(ModelConfig)
                .where(ModelConfig.role == ModelRole.continuation, ModelConfig.is_active == True)
                .limit(1)
            )
            config = result.scalar_one_or_none()
        if not config:
            raise ValueError("No polishing model configured")

        text_to_polish = chapter.content if full_chapter else chapter.content[-5000:]

        provider = self.registry.get_or_create(config)
        response = await provider.generate([
            {"role": "system", "content": POLISHING_SYSTEM},
            {"role": "user", "content": POLISHING_USER.format(text=text_to_polish)},
        ])

        original = text_to_polish
        polished = response.content

        if full_chapter:
            chapter.content = polished
        else:
            chapter.content = chapter.content[:-len(original)] + polished

        chapter.status = ChapterStatus.polished
        await db.commit()

        return original, polished

    async def polish_stream(self, db: AsyncSession, chapter_id: str, text: str):
        """Stream polish the given text."""
        config_result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.role == ModelRole.polishing, ModelConfig.is_active == True)
            .limit(1)
        )
        config = config_result.scalar_one_or_none()
        if not config:
            result = await db.execute(
                select(ModelConfig)
                .where(ModelConfig.role == ModelRole.continuation, ModelConfig.is_active == True)
                .limit(1)
            )
            config = result.scalar_one_or_none()
        if not config:
            raise ValueError("No polishing model configured")

        provider = self.registry.get_or_create(config)
        async for chunk in provider.generate_stream([
            {"role": "system", "content": POLISHING_SYSTEM},
            {"role": "user", "content": POLISHING_USER.format(text=text)},
        ]):
            yield chunk
