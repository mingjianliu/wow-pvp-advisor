import pytest
from wow_advisor.api.models import GearSlot
from wow_advisor.processor.gear import aggregate_gear


def make_slot(slot: str, item_id: int, item_name: str, ilvl: int,
              enchant_id: int | None = None, enchant_name: str | None = None) -> GearSlot:
    return GearSlot(slot=slot, item_id=item_id, item_name=item_name, ilvl=ilvl,
                    enchant_id=enchant_id, enchant_name=enchant_name)


def test_aggregate_item_frequency():
    # 3 players have Hood A, 1 has Hood B
    players_gear = (
        [make_slot("head", 100, "Hood A", 639)] * 3 +
        [make_slot("head", 101, "Hood B", 636)]
    )
    # Each player has a single-item list
    gear_per_player = [[slot] for slot in players_gear]
    result = aggregate_gear(gear_per_player, n_players=4)
    head_items = result["gear"]["head"]
    assert head_items[0]["item_id"] == 100
    assert head_items[0]["count"] == 3
    assert head_items[0]["pct"] == 75.0


def test_aggregate_enchant_frequency():
    gear_per_player = [
        [make_slot("chest", 200, "Chest", 639, enchant_id=7459, enchant_name="Crystalline")],
        [make_slot("chest", 200, "Chest", 639, enchant_id=7459, enchant_name="Crystalline")],
        [make_slot("chest", 200, "Chest", 639)],
    ]
    result = aggregate_gear(gear_per_player, n_players=3)
    enchants = result["enchants"].get("chest", [])
    assert len(enchants) == 1
    assert enchants[0]["enchant_id"] == 7459
    assert enchants[0]["count"] == 2
    assert round(enchants[0]["pct"], 1) == 66.7


def test_aggregate_avg_ilvl():
    gear_per_player = [[make_slot("head", 100, "Hood", 639)] for _ in range(3)]
    result = aggregate_gear(gear_per_player, n_players=3, equipped_ilvls=[639, 636, 633])
    assert result["avg_ilvl"] == 636


def test_aggregate_empty():
    result = aggregate_gear([], n_players=0)
    assert result["gear"] == {}
    assert result["enchants"] == {}
    assert result["avg_ilvl"] == 0


def test_aggregate_trinkets_surfaced():
    gear_per_player = [
        [
            make_slot("trinket_1", 300, "Trinket A", 639),
            make_slot("trinket_2", 301, "Trinket B", 639),
        ]
        for _ in range(5)
    ]
    result = aggregate_gear(gear_per_player, n_players=5)
    assert "trinket_1" in result["gear"]
    assert result["gear"]["trinket_1"][0]["item_id"] == 300
    assert result["gear"]["trinket_1"][0]["pct"] == 100.0
