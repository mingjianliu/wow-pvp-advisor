from dataclasses import dataclass, field


@dataclass
class LeaderboardEntry:
    name: str
    realm: str
    rating: int
    rank: int


@dataclass
class GearSlot:
    slot: str
    item_id: int
    item_name: str
    ilvl: int
    enchant_id: int | None = None
    enchant_name: str | None = None


@dataclass
class TalentData:
    loadout_code: str
    class_node_ids: list[int] = field(default_factory=list)
    spec_node_ids: list[int] = field(default_factory=list)
    hero_node_ids: list[int] = field(default_factory=list)

    @property
    def all_node_ids(self) -> set[int]:
        return set(self.class_node_ids + self.spec_node_ids + self.hero_node_ids)


@dataclass
class CharacterData:
    name: str
    realm: str
    region: str
    character_class: str
    spec: str
    equipped_ilvl: int
    rating: int
    talent: TalentData | None = None
    gear: list[GearSlot] = field(default_factory=list)
