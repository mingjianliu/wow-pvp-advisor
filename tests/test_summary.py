import pytest
from wow_advisor.tools.summary import _enrich_talents


NODE_MAP = {
    100: {"name": "Lightning Bolt", "row": 1, "col": 3, "type": "single",
          "max_rank": 1, "icon": "123", "children": []},
    101: {"name": "Chain Lightning", "row": 2, "col": 3, "type": "single",
          "max_rank": 1, "icon": "124", "children": []},
    200: {"name": "Stormkeeper", "row": 3, "col": 2, "type": "single",
          "max_rank": 1, "icon": "125", "children": []},
    201: {"name": "Tempest", "row": 3, "col": 4, "type": "single",
          "max_rank": 1, "icon": "126", "children": []},
}

RAW_TALENTS = {
    "core_nodes": [100, 101],
    "flex_nodes": [],
    "contested_nodes": [200],
    "clusters": [
        {"rank": 1, "pct": 72.0, "canonical_code": "abc", "takes": [200], "skips": [201]},
        {"rank": 2, "pct": 28.0, "canonical_code": "def", "takes": [201], "skips": [200]},
    ],
    "clustering_method": "variance+hamming",
}


def test_enrich_renames_keys():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert "core" in result
    assert "flex" in result
    assert "contested" in result
    assert "core_nodes" not in result
    assert "flex_nodes" not in result
    assert "contested_nodes" not in result


def test_enrich_core_contains_id_and_name():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert result["core"] == [
        {"id": 100, "name": "Lightning Bolt"},
        {"id": 101, "name": "Chain Lightning"},
    ]


def test_enrich_cluster_takes_and_skips():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    cluster = result["clusters"][0]
    assert cluster["takes"] == [{"id": 200, "name": "Stormkeeper"}]
    assert cluster["skips"] == [{"id": 201, "name": "Tempest"}]


def test_enrich_preserves_non_talent_cluster_fields():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    cluster = result["clusters"][0]
    assert cluster["rank"] == 1
    assert cluster["pct"] == 72.0
    assert cluster["canonical_code"] == "abc"


def test_enrich_preserves_clustering_method():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert result["clustering_method"] == "variance+hamming"


def test_enrich_null_name_when_node_not_in_map():
    result = _enrich_talents(RAW_TALENTS, {})
    assert result["core"][0] == {"id": 100, "name": None}
    assert result["clusters"][0]["takes"][0] == {"id": 200, "name": None}


def test_enrich_empty_flex():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert result["flex"] == []
