import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.story import Chapter
from ..models.foreshadowing import Foreshadowing, ForeshadowingStatus
from ..models.model_config import ModelConfig, ModelRole
from ..providers.registry import ProviderRegistry
from ..utils.prompt_templates import FORESHADOWING_DETECTION


class ForeshadowingService:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    async def detect_in_chapter(self, db: AsyncSession, story_id: str, chapter_id: str) -> list[Foreshadowing]:
        """Analyze a chapter for new or progressed foreshadowings."""
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or not chapter.content:
            return []

        result = await db.execute(
            select(Foreshadowing)
            .where(
                Foreshadowing.story_id == story_id,
                Foreshadowing.status.in_([ForeshadowingStatus.planted, ForeshadowingStatus.developing]),
            )
        )
        existing = result.scalars().all()

        existing_text = "\n".join(
            f"ID: {f.id} | {f.title}: {f.description[:100]}" for f in existing
        ) or "无"

        config = await self._get_analysis_config(db)
        if not config:
            return []

        provider = self.registry.get_or_create(config)
        response = await provider.generate([
            {"role": "user", "content": FORESHADOWING_DETECTION.format(
                existing_foreshadowings=existing_text,
                chapter_content=chapter.content[:15000],
            )}
        ])

        try:
            text = response.content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        results = []

        for fp_data in data.get("new_foreshadowings", []):
            fp = Foreshadowing(
                story_id=story_id,
                title=fp_data.get("title", ""),
                description=fp_data.get("description", ""),
                plant_chapter_id=chapter_id,
                status=ForeshadowingStatus.planted,
                priority=fp_data.get("priority", 3),
                related_entries=fp_data.get("related_characters", []),
            )
            db.add(fp)
            results.append(fp)

        for prog_data in data.get("progressed_foreshadowings", []):
            fp = await self._find_foreshadowing(db, existing, prog_data.get("id", ""))
            if fp:
                fp.status = ForeshadowingStatus.developing
                fp.notes = (fp.notes or "") + f"\n[推进] {prog_data.get('progress', '')}"
                results.append(fp)

        for rev_data in data.get("revealed_foreshadowings", []):
            fp = await self._find_foreshadowing(db, existing, rev_data.get("id", ""))
            if fp:
                fp.status = ForeshadowingStatus.revealed
                fp.reveal_chapter_id = chapter_id
                fp.notes = (fp.notes or "") + f"\n[揭示] {rev_data.get('reveal_description', '')}"
                results.append(fp)

        await db.commit()
        return results

    def _find_foreshadowing(self, db: AsyncSession, existing: list[Foreshadowing], id_or_title: str) -> Foreshadowing | None:
        for fp in existing:
            if fp.id == id_or_title or fp.title == id_or_title:
                return fp
        return None

    async def _get_analysis_config(self, db: AsyncSession) -> ModelConfig | None:
        result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.role == ModelRole.foreshadowing, ModelConfig.is_active == True)
            .limit(1)
        )
        config = result.scalar_one_or_none()
        if not config:
            result = await db.execute(
                select(ModelConfig).where(ModelConfig.is_active == True).limit(1)
            )
            config = result.scalar_one_or_none()
        return config
