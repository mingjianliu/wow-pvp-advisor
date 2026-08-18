"""Tests for BnetClient.fetch_talent_nodes — the parser feeding the talent name cache.

Node payloads mirror the real 12.1 static API shape (build 12.1.0_68914).
"""
import httpx
import pytest
import respx
from unittest.mock import AsyncMock

from wow_advisor.api.client import BnetClient

TREE_URL = "https://us.api.blizzard.com/data/wow/talent-tree/786/playable-specialization/71"
NAMESPACE = "static-12.1.0_68914-us"

# Arms Warrior node 92614 as it exists in 12.1: a two-option choice node.
CHOICE_NODE = {
    "id": 92614,
    "node_type": {"id": 2, "type": "CHOICE"},
    "display_row": 7,
    "display_col": 16,
    "unlocks": [90285, 109680],
    "ranks": [
        {
            "rank": 1,
            "choice_of_tooltips": [
                {
                    "talent": {"name": "Overpowering Finish", "id": 119740},
                    "spell_tooltip": {"spell": {"name": "Overpowering Finish", "id": 400205}},
                },
                {
                    "talent": {"name": "Mass Execution", "id": 142233},
                    "spell_tooltip": {"spell": {"name": "Mass Execution", "id": 1273075}},
                },
            ],
        }
    ],
}

PASSIVE_NODE = {
    "id": 92615,
    "node_type": {"id": 1, "type": "PASSIVE"},
    "display_row": 3,
    "display_col": 9,
    "unlocks": [],
    "ranks": [
        {
            "rank": 1,
            "tooltip": {
                "talent": {"name": "Master Tactician", "id": 117238},
                "spell_tooltip": {"spell": {"name": "Master Tactician", "id": 384124}},
            },
        }
    ],
}


@pytest.fixture
def client():
    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    return BnetClient(auth=auth, region="us")


def _tree_response(nodes):
    return httpx.Response(
        200,
        json={"class_talent_nodes": nodes, "spec_talent_nodes": []},
        headers={
            "Last-Modified": "Fri, 14 Aug 2026 14:34:00 GMT",
            "Battlenet-Namespace": NAMESPACE,
        },
    )


@respx.mock
async def test_choice_node_name_lists_both_options(client):
    """Choice nodes carry no ranks[].tooltip — the name must come from choice_of_tooltips.

    Regression: every CHOICE node used to resolve to name=None, which dropped the
    highest-weight build-defining nodes out of summaries and HTML reports entirely.
    """
    respx.get(TREE_URL).mock(return_value=_tree_response([CHOICE_NODE]))

    nodes, _, _, _ = await client.fetch_talent_nodes(786, 71)

    assert nodes[92614]["name"] == "Overpowering Finish / Mass Execution"


@respx.mock
async def test_choice_node_exposes_each_option_separately(client):
    respx.get(TREE_URL).mock(return_value=_tree_response([CHOICE_NODE]))

    nodes, _, _, _ = await client.fetch_talent_nodes(786, 71)

    assert nodes[92614]["choices"] == ["Overpowering Finish", "Mass Execution"]


@respx.mock
async def test_choice_node_icon_uses_first_option_spell(client):
    respx.get(TREE_URL).mock(return_value=_tree_response([CHOICE_NODE]))

    nodes, _, _, _ = await client.fetch_talent_nodes(786, 71)

    assert nodes[92614]["icon"] == "400205"


@respx.mock
async def test_passive_node_keeps_single_name_and_no_choices(client):
    respx.get(TREE_URL).mock(return_value=_tree_response([PASSIVE_NODE]))

    nodes, _, _, _ = await client.fetch_talent_nodes(786, 71)

    assert nodes[92615]["name"] == "Master Tactician"
    assert nodes[92615]["choices"] == []


@respx.mock
async def test_fetch_reports_game_build_from_namespace_header(client):
    """The build stamp is what lets callers notice that node IDs were reshuffled.

    Blizzard reassigns talents across node IDs between builds (12.1 swapped
    Battlelord and Master Tactician), so cached data keyed by node ID is only
    interpretable against the build it was captured under.
    """
    respx.get(TREE_URL).mock(return_value=_tree_response([PASSIVE_NODE]))

    _, _, _, game_build = await client.fetch_talent_nodes(786, 71)

    assert game_build == "12.1.0_68914"


@respx.mock
async def test_fetch_reports_no_build_when_header_absent(client):
    respx.get(TREE_URL).mock(
        return_value=httpx.Response(
            200,
            json={"class_talent_nodes": [PASSIVE_NODE], "spec_talent_nodes": []},
            headers={"Last-Modified": "Fri, 14 Aug 2026 14:34:00 GMT"},
        )
    )

    _, _, _, game_build = await client.fetch_talent_nodes(786, 71)

    assert game_build is None
