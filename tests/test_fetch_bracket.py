"""Shared-ladder collection: one scan serving every spec and every locale."""
import pytest
from unittest.mock import ANY, MagicMock, patch, AsyncMock

from wow_advisor.api.models import CharacterData, LeaderboardEntry, LeaderboardPage
from wow_advisor.tools.fetch import _scan_ladder, _localize, fetch_bracket_async

SHAMAN_RESTO = (7, 264)
MAGE_FROST = (8, 64)


def entry(i):
    return LeaderboardEntry(rank=i, rating=3000 - i, name=f"P{i}", realm="area-52")


def char(i, ids):
    return CharacterData(
        name=f"P{i}", realm="area-52", region="us", character_class="Shaman",
        spec="Restoration", equipped_ilvl=630, rating=3000 - i,
        class_id=ids[0], spec_id=ids[1],
    )


@pytest.mark.asyncio
async def test_scan_ladder_buckets_every_spec_in_one_pass():
    # The whole point: two specs come out of a single pass over the ladder.
    chars = [char(0, SHAMAN_RESTO), char(1, MAGE_FROST), char(2, SHAMAN_RESTO)]
    client = MagicMock()
    client.fetch_character_spec = AsyncMock(side_effect=chars)

    buckets = await _scan_ladder(
        client, [entry(i) for i in range(3)],
        {SHAMAN_RESTO: "restoration-shaman", MAGE_FROST: "frost-mage"},
        limit=50,
    )

    assert [c.name for c in buckets["restoration-shaman"]] == ["P0", "P2"]
    assert [c.name for c in buckets["frost-mage"]] == ["P1"]
    assert client.fetch_character_spec.call_count == 3  # not 3 per spec


@pytest.mark.asyncio
async def test_scan_ladder_stops_once_every_bucket_is_full():
    # 60 entries, batch size 50: the second batch must not be fetched once both
    # targets filled in the first.
    chars = [char(i, SHAMAN_RESTO if i % 2 else MAGE_FROST) for i in range(60)]
    client = MagicMock()
    client.fetch_character_spec = AsyncMock(side_effect=chars)

    buckets = await _scan_ladder(
        client, [entry(i) for i in range(60)],
        {SHAMAN_RESTO: "restoration-shaman", MAGE_FROST: "frost-mage"},
        limit=2,
    )

    assert len(buckets["restoration-shaman"]) == 2
    assert len(buckets["frost-mage"]) == 2
    assert client.fetch_character_spec.call_count == 50


@pytest.mark.asyncio
async def test_scan_ladder_keeps_scanning_while_a_bucket_is_short():
    # A rare spec that never fills must not stop the pass early...
    chars = [char(i, SHAMAN_RESTO) for i in range(60)]
    client = MagicMock()
    client.fetch_character_spec = AsyncMock(side_effect=chars)

    buckets = await _scan_ladder(
        client, [entry(i) for i in range(60)],
        {SHAMAN_RESTO: "restoration-shaman", MAGE_FROST: "frost-mage"},
        limit=50,
    )

    assert len(buckets["restoration-shaman"]) == 50
    assert buckets["frost-mage"] == []
    assert client.fetch_character_spec.call_count == 60  # ...the full ladder


@pytest.mark.asyncio
async def test_localize_relabels_without_refetching_profiles():
    client = MagicMock()
    client.fetch_spec_labels = AsyncMock(return_value=("萨满祭司", "恢复"))
    scanned = [char(0, SHAMAN_RESTO), char(1, SHAMAN_RESTO)]

    out = await _localize(client, scanned, "restoration-shaman", "zh_CN", "en_US")

    assert [c.character_class for c in out] == ["萨满祭司", "萨满祭司"]
    assert [c.spec for c in out] == ["恢复", "恢复"]
    # One static lookup for the whole roster, and the scan's objects untouched.
    assert client.fetch_spec_labels.call_count == 1
    assert scanned[0].character_class == "Shaman"


@pytest.mark.asyncio
async def test_localize_skips_lookup_for_the_scan_locale():
    client = MagicMock()
    client.fetch_spec_labels = AsyncMock()

    out = await _localize(client, [char(0, SHAMAN_RESTO)], "restoration-shaman", "en_US", "en_US")

    client.fetch_spec_labels.assert_not_called()
    assert out[0].character_class == "Shaman"
    assert out[0] is not None


@pytest.mark.asyncio
async def test_localize_keeps_scan_labels_when_lookup_fails():
    # Display names are an enrichment; losing them must not fail the collection.
    client = MagicMock()
    client.fetch_spec_labels = AsyncMock(return_value=None)

    out = await _localize(client, [char(0, SHAMAN_RESTO)], "restoration-shaman", "zh_CN", "en_US")

    assert out[0].character_class == "Shaman"


@pytest.mark.asyncio
async def test_fetch_bracket_scans_once_for_two_specs_and_two_locales():
    ladder = [entry(i) for i in range(2)]
    scanned = [char(0, SHAMAN_RESTO), char(1, MAGE_FROST)]

    with patch("wow_advisor.tools.fetch.get_default_db") as db, \
         patch("wow_advisor.tools.fetch.CacheStore") as store_cls, \
         patch("wow_advisor.tools.fetch._make_client") as make_client, \
         patch("wow_advisor.tools.fetch.build_aggregation") as build_agg:
        db.return_value = MagicMock()
        store = MagicMock()
        store_cls.return_value = store
        build_agg.return_value = {"sample_size": 1}

        client = MagicMock()
        client.fetch_leaderboard = AsyncMock(
            return_value=LeaderboardPage(entries=ladder, season_id=42))
        client.fetch_character_spec = AsyncMock(side_effect=scanned)
        client.fetch_character_details = AsyncMock(side_effect=lambda name, realm, char, locale: char)
        client.fetch_spec_labels = AsyncMock(return_value=("萨满祭司", "恢复"))
        make_client.return_value = (MagicMock(), client)

        out = await fetch_bracket_async(
            "3v3", locales=("en_US", "zh_CN"),
            specs=["restoration-shaman", "frost-mage"],
        )

    # One ladder fetch and one profile per entry — not one pass per (spec, locale).
    client.fetch_leaderboard.assert_called_once_with(bracket="3v3")
    assert client.fetch_character_spec.call_count == 2
    # 2 specs x 2 locales of phase 2 + cache writes
    assert client.fetch_character_details.call_count == 4
    assert store.save_aggregation.call_count == 4
    assert out["season_id"] == 42
    assert len(out["results"]) == 4
    assert {r["locale"] for r in out["results"]} == {"en_US", "zh_CN"}


@pytest.mark.asyncio
async def test_fetch_bracket_reports_specs_with_no_players():
    ladder = [entry(0)]
    with patch("wow_advisor.tools.fetch.get_default_db"), \
         patch("wow_advisor.tools.fetch.CacheStore"), \
         patch("wow_advisor.tools.fetch._make_client") as make_client, \
         patch("wow_advisor.tools.fetch.build_aggregation") as build_agg:
        build_agg.return_value = {"sample_size": 1}
        client = MagicMock()
        client.fetch_leaderboard = AsyncMock(
            return_value=LeaderboardPage(entries=ladder, season_id=42))
        client.fetch_character_spec = AsyncMock(side_effect=[char(0, SHAMAN_RESTO)])
        client.fetch_character_details = AsyncMock(side_effect=lambda name, realm, char, locale: char)
        make_client.return_value = (MagicMock(), client)

        out = await fetch_bracket_async(
            "3v3", specs=["restoration-shaman", "frost-mage"])

    absent = [r for r in out["results"] if r["spec"] == "frost-mage"]
    assert absent and absent[0]["fetched"] == 0 and "no frost-mage players" in absent[0]["note"]


@pytest.mark.asyncio
async def test_fetch_bracket_rejects_unknown_spec():
    out = await fetch_bracket_async("3v3", specs=["restoration-shaman", "not-a-spec"])
    assert "not-a-spec" in out["error"]


@pytest.mark.asyncio
async def test_fetch_bracket_uses_per_spec_boards_for_solo_shuffle():
    with patch("wow_advisor.tools.fetch.get_default_db"), \
         patch("wow_advisor.tools.fetch.CacheStore"), \
         patch("wow_advisor.tools.fetch._make_client") as make_client, \
         patch("wow_advisor.tools.fetch.build_aggregation") as build_agg:
        build_agg.return_value = {"sample_size": 1}
        client = MagicMock()
        client.fetch_leaderboard = AsyncMock(
            return_value=LeaderboardPage(entries=[entry(0)], season_id=42))
        client.fetch_character_spec = AsyncMock(side_effect=[char(0, SHAMAN_RESTO)])
        client.fetch_character_details = AsyncMock(side_effect=lambda name, realm, char, locale: char)
        make_client.return_value = (MagicMock(), client)

        await fetch_bracket_async("solo-shuffle", specs=["restoration-shaman"])

    client.fetch_leaderboard.assert_called_once_with(bracket="shuffle-shaman-restoration")
