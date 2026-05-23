import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.story import Chapter
from ..models.world_book import WorldBookEntry, CharacterRelation, EntryCategory, EntryStatus
from ..models.model_config import ModelConfig, ModelRole
from ..providers.registry import ProviderRegistry
from ..utils.prompt_templates import WORLD_ANALYSIS_PROMPT


class WorldAnalysisService:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    async def analyze_chapter(self, db: AsyncSession, story_id: str, chapter_id: str) -> list[WorldBookEntry]:
        """Analyze a chapter and update the world book. Returns new/updated entries."""
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or not chapter.content:
            return []

        config = await self._get_analysis_config(db)
        if not config:
            return []

        provider = self.registry.get_or_create(config)
        response = await provider.generate([
            {"role": "user", "content": WORLD_ANALYSIS_PROMPT.format(chapter_content=chapter.content[:15000])}
        ])

        try:
            data = self._parse_json(response.content)
        except json.JSONDecodeError:
            return []

        new_entries = []

        for char_data in data.get("new_characters", []):
            entry = await self._create_character(db, story_id, chapter_id, char_data)
            new_entries.append(entry)

        for update_data in data.get("updated_characters", []):
            entry = await self._update_character(db, story_id, update_data)
            if entry:
                new_entries.append(entry)

        for loc_data in data.get("new_locations", []):
            entry = await self._create_entry(db, story_id, chapter_id, EntryCategory.location, loc_data)
            new_entries.append(entry)

        for faction_data in data.get("new_factions", []):
            entry = await self._create_entry(db, story_id, chapter_id, EntryCategory.faction, faction_data)
            new_entries.append(entry)

        for item_data in data.get("new_items", []):
            entry = await self._create_entry(db, story_id, chapter_id, EntryCategory.item, item_data)
            new_entries.append(entry)

        await db.commit()
        return new_entries

    async def _create_character(self, db: AsyncSession, story_id: str, chapter_id: str, data: dict) -> WorldBookEntry:
        new_name = data.get("name", "")
        new_aliases = data.get("aliases", [])

        # Tier 1: exact name match
        existing = await db.execute(
            select(WorldBookEntry).where(
                WorldBookEntry.story_id == story_id,
                WorldBookEntry.name == new_name,
                WorldBookEntry.category == EntryCategory.character,
            )
        )
        if existing.scalar_one_or_none():
            return None

        # Tier 2: alias matching — check all characters in this story
        all_chars = await db.execute(
            select(WorldBookEntry).where(
                WorldBookEntry.story_id == story_id,
                WorldBookEntry.category == EntryCategory.character,
            )
        )
        for char in all_chars.scalars().all():
            char_aliases = char.aliases or []
            if new_name in char_aliases:
                return None
            if new_name == char.name:
                return None
            for alias in new_aliases:
                if alias == char.name or alias in char_aliases:
                    return None

        attrs = {
            "gender": data.get("gender", "未知"),
            "age": data.get("age", ""),
            "appearance": data.get("appearance", ""),
            "identity": data.get("identity", ""),
            "personality": data.get("personality", []),
            "abilities": data.get("abilities", []),
            "catchphrases": data.get("catchphrases", []),
        }

        entry = WorldBookEntry(
            story_id=story_id,
            category=EntryCategory.character,
            name=data.get("name", ""),
            aliases=data.get("aliases", []),
            description=data.get("description", ""),
            attributes=attrs,
            importance=data.get("importance", 3),
            source_chapter_id=chapter_id,
        )
        db.add(entry)
        return entry

    async def _update_character(self, db: AsyncSession, story_id: str, data: dict) -> WorldBookEntry | None:
        name = data.get("name", "")
        result = await db.execute(
            select(WorldBookEntry).where(
                WorldBookEntry.story_id == story_id,
                WorldBookEntry.name == name,
                WorldBookEntry.category == EntryCategory.character,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None

        attrs = entry.attributes or {}
        if data.get("new_abilities"):
            existing_abilities = attrs.get("abilities", [])
            for ab in data["new_abilities"]:
                if ab not in existing_abilities:
                    existing_abilities.append(ab)
            attrs["abilities"] = existing_abilities

        if data.get("status_change"):
            attrs["status_note"] = data["status_change"]

        if data.get("changes"):
            desc_parts = [entry.description or ""]
            desc_parts.append(f"[更新] {data['changes']}")
            entry.description = "\n".join(desc_parts)

        entry.attributes = attrs
        entry.version += 1

        for rel_data in data.get("new_relationships", []):
            target_result = await db.execute(
                select(WorldBookEntry).where(
                    WorldBookEntry.story_id == story_id,
                    WorldBookEntry.name == rel_data["target"],
                    WorldBookEntry.category == EntryCategory.character,
                )
            )
            target = target_result.scalar_one_or_none()
            if target:
                relation = CharacterRelation(
                    story_id=story_id,
                    source_char_id=entry.id,
                    target_char_id=target.id,
                    relation_type=rel_data.get("type", ""),
                    description=rel_data.get("description", ""),
                )
                db.add(relation)

        return entry

    async def _create_entry(self, db: AsyncSession, story_id: str, chapter_id: str, category: EntryCategory, data: dict) -> WorldBookEntry:
        new_name = data.get("name", "")

        # Tier 1: exact name match
        existing = await db.execute(
            select(WorldBookEntry).where(
                WorldBookEntry.story_id == story_id,
                WorldBookEntry.name == new_name,
                WorldBookEntry.category == category,
            )
        )
        if existing.scalar_one_or_none():
            return None

        # Tier 2: alias match
        all_entries = await db.execute(
            select(WorldBookEntry).where(
                WorldBookEntry.story_id == story_id,
                WorldBookEntry.category == category,
            )
        )
        for entry in all_entries.scalars().all():
            if new_name in (entry.aliases or []):
                return None

        entry = WorldBookEntry(
            story_id=story_id,
            category=category,
            name=data.get("name", ""),
            description=data.get("description", ""),
            attributes={"features": data.get("features", []), "members": data.get("members", []), "significance": data.get("significance", "")},
            importance=3,
            source_chapter_id=chapter_id,
        )
        db.add(entry)
        return entry

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)

    async def _get_analysis_config(self, db: AsyncSession) -> ModelConfig | None:
        result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.role == ModelRole.world_analysis, ModelConfig.is_active == True)
            .limit(1)
        )
        config = result.scalar_one_or_none()
        if not config:
            result = await db.execute(
                select(ModelConfig).where(ModelConfig.is_active == True).limit(1)
            )
            config = result.scalar_one_or_none()
        return config
