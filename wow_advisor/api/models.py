from dataclasses import dataclass, field


@dataclass
class LeaderboardEntry:
    name: str
    realm: str
    rating: int
    rank: int


@dataclass
class LeaderboardPage:
    """Leaderboard entries plus which season actually produced them.

    season_id is recorded because it is not always the current season: on day one
    of a new season the ladder is empty, and falling back to the previous season
    is only acceptable if callers can see that it happened.
    """
    entries: list[LeaderboardEntry]
    season_id: int
    is_fallback: bool = False


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
    pvp_talent_ids: list[int] = field(default_factory=list)
    pvp_talent_names: list[str] = field(default_factory=list)
    node_ranks: dict[int, int] = field(default_factory=dict)

    @property
    def all_node_ids(self) -> set[int]:
        if self.node_ranks:
            return set(self.node_ranks.keys())
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
    class_id: int = 0
    spec_id: int = 0
    talent: TalentData | None = None
    gear: list[GearSlot] = field(default_factory=list)
