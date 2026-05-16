from collections import Counter, defaultdict
from wow_advisor.api.models import GearSlot


def aggregate_gear(
    gear_per_player: list[list[GearSlot]],
    n_players: int,
    equipped_ilvls: list[int] | None = None,
) -> dict:
    if n_players == 0:
        return {"gear": {}, "enchants": {}, "avg_ilvl": 0}

    slot_items: dict[str, list[tuple[int, str]]] = defaultdict(list)
    slot_enchants: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for player_gear in gear_per_player:
        for g in player_gear:
            slot_items[g.slot].append((g.item_id, g.item_name))
            if g.enchant_id is not None:
                slot_enchants[g.slot].append((g.enchant_id, g.enchant_name or ""))

    gear_summary: dict[str, list[dict]] = {}
    for slot, items in slot_items.items():
        counts = Counter(items)
        gear_summary[slot] = sorted(
            [
                {
                    "item_id": item_id,
                    "name": item_name,
                    "count": count,
                    "pct": round(count / n_players * 100, 1),
                }
                for (item_id, item_name), count in counts.items()
            ],
            key=lambda x: -x["count"],
        )

    enchant_summary: dict[str, list[dict]] = {}
    for slot, enchants in slot_enchants.items():
        counts = Counter(enchants)
        enchant_summary[slot] = sorted(
            [
                {
                    "enchant_id": eid,
                    "name": ename,
                    "count": count,
                    "pct": round(count / n_players * 100, 1),
                }
                for (eid, ename), count in counts.items()
            ],
            key=lambda x: -x["count"],
        )

    if equipped_ilvls:
        avg_ilvl = round(sum(equipped_ilvls) / len(equipped_ilvls))
    else:
        avg_ilvl = 0

    return {"gear": gear_summary, "enchants": enchant_summary, "avg_ilvl": avg_ilvl}
