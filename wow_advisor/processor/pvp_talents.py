"""Diffing PvP talent pools between two snapshots of the game.

PvP talents are only ever observed through player profiles, which show what the
top 50 happened to pick — not what the pool contains. A talent nobody ran is
indistinguishable from one that was deleted. Snapshotting the whole pool per
spec turns "did 12.1 change PvP talents?" into a diff instead of a patch-note
reading exercise.
"""


def diff_pvp_talent_pool(old: list[dict], new: list[dict]) -> dict:
    """Compare two pools of {"id", "name"} entries.

    Talent IDs are the identity; a changed name under a stable ID is a rename,
    not an add plus a remove.
    """
    old_by_id = {t["id"]: t for t in old}
    new_by_id = {t["id"]: t for t in new}

    added = [new_by_id[i] for i in sorted(new_by_id.keys() - old_by_id.keys())]
    removed = [old_by_id[i] for i in sorted(old_by_id.keys() - new_by_id.keys())]
    renamed = [
        {"id": i, "from": old_by_id[i]["name"], "to": new_by_id[i]["name"]}
        for i in sorted(old_by_id.keys() & new_by_id.keys())
        if old_by_id[i]["name"] != new_by_id[i]["name"]
    ]
    return {"added": added, "removed": removed, "renamed": renamed}


async def refresh_pvp_talent_pools(
    store,
    client,
    specs: list[str],
    locale: str = "en_US",
    save: bool = False,
    concurrency: int = 8,
) -> dict[str, dict]:
    """Fetch each spec's current pool and report it against the stored snapshot.

    Returns {spec: {"status", ...}} where status is one of "new" (no baseline
    yet), "changed" (with a "diff"), "unchanged", or "unknown-spec". Nothing is
    written unless save=True, so the same call powers both a dry run and the
    real refresh.
    """
    import asyncio

    from wow_advisor.normalize import spec_to_ids

    sem = asyncio.Semaphore(concurrency)

    async def one(spec: str) -> tuple[str, dict]:
        ids = spec_to_ids(spec)
        if ids is None:
            return spec, {"status": "unknown-spec"}
        async with sem:
            talents, game_build = await client.fetch_pvp_talents(ids[1], locale=locale)

        previous = store.get_pvp_talent_pool(spec, locale=locale)
        if previous is None:
            entry = {"status": "new", "count": len(talents), "game_build": game_build}
        else:
            d = diff_pvp_talent_pool(previous, talents)
            if any(d.values()):
                entry = {
                    "status": "changed",
                    "diff": d,
                    "game_build": game_build,
                    "previous_game_build": store.pvp_talent_pool_game_build(spec, locale=locale),
                }
            else:
                entry = {"status": "unchanged", "count": len(talents), "game_build": game_build}

        if save:
            store.save_pvp_talent_pool(spec, talents, locale=locale, game_build=game_build)
        return spec, entry

    return dict(await asyncio.gather(*[one(s) for s in specs]))
