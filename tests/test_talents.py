import pytest
from wow_advisor.processor.talents import (
    TalentAnalysis,
    analyze_talents,
    cluster_talents,
    summarize_talent_clusters,
    _weighted_distance,
)


def make_node_sets(count: int, base: list[int], contested: dict[int, list[int]]) -> list[set[int]]:
    """Build `count` talent node sets. contested maps node_id → indices of players who take it."""
    result = [set(base) for _ in range(count)]
    for node_id, takers in contested.items():
        for i in takers:
            result[i].add(node_id)
    return result


def test_analyze_identifies_core_nodes():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(5)), 20: [0]})
    analysis = analyze_talents(node_sets)
    assert 1 in analysis.core_nodes
    assert 2 in analysis.core_nodes
    assert 3 in analysis.core_nodes


def test_analyze_identifies_contested_nodes():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(5)), 20: [0]})
    analysis = analyze_talents(node_sets)
    assert 10 in analysis.contested_nodes


def test_analyze_identifies_flex_nodes():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(5)), 20: [0]})
    analysis = analyze_talents(node_sets)
    assert 20 in analysis.flex_nodes


def test_analyze_empty_input():
    analysis = analyze_talents([])
    assert analysis.core_nodes == set()
    assert analysis.contested_nodes == set()
    assert analysis.flex_nodes == set()


def test_cluster_splits_distinct_builds():
    # 5 players take node 100, 5 take node 101 — hamming distance = 2, threshold = 1 → 2 clusters
    pairs = [({100}, i) for i in range(5)] + [({101}, i + 5) for i in range(5)]
    clusters = cluster_talents(pairs, threshold=1)
    assert len(clusters) == 2
    assert sorted(len(c) for c in clusters) == [5, 5]


def test_cluster_merges_near_identical():
    # {100} vs {100, 101} differ by 1 node — within threshold=2 → 1 cluster
    pairs = [({100}, i) for i in range(5)] + [({100, 101}, i + 5) for i in range(5)]
    clusters = cluster_talents(pairs, threshold=2)
    assert len(clusters) == 1


def test_cluster_sorted_by_size_descending():
    # 7 players take {100}, 3 take {101}
    pairs = [({100}, i) for i in range(7)] + [({101}, i + 7) for i in range(3)]
    clusters = cluster_talents(pairs, threshold=1)
    assert len(clusters[0]) >= len(clusters[1])


def test_full_pipeline_two_builds():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(7)), 11: list(range(7, 10))})
    analysis = analyze_talents(node_sets)
    contested_pairs = [(node_sets[i] & analysis.contested_nodes, i) for i in range(10)]
    clusters = cluster_talents(contested_pairs, threshold=1)
    assert len(clusters) == 2
    sizes = sorted([len(c) for c in clusters], reverse=True)
    assert sizes == [7, 3]


def test_summarize_returns_expected_shape():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(7)), 11: list(range(7, 10))})
    codes = [f"code_{i}" for i in range(10)]
    result = summarize_talent_clusters(node_sets, codes, keystone_nodes=None)
    assert "core_nodes" in result
    assert "contested_nodes" in result
    assert "clusters" in result
    assert result["clustering_method"] in ("variance+hamming", "keystone")
    assert len(result["clusters"]) == 2
    assert result["clusters"][0]["pct"] == 70.0


def test_analyze_includes_node_meta():
    node_sets = [{1}]
    node_meta = {1: {"row": 0, "type": "circle"}}
    analysis = analyze_talents(node_sets, node_meta=node_meta)
    assert analysis.node_meta == node_meta
def test_weighted_distance_basic():
    set_a = {1}
    ranks_a = {1: 1}
    set_b = set()
    ranks_b = {}
    node_meta = {1: {"row": 0, "type": "circle"}}  # Utility node
    
    # Distance should be 2.0 for utility node difference
    assert _weighted_distance(set_a, ranks_a, set_b, ranks_b, node_meta) == 2.0


def test_weighted_distance_node_types():
    set_a = {1, 2, 3}
    ranks_a = {1: 1, 2: 1, 3: 1}
    set_b = set()
    ranks_b = {}
    node_meta = {
        1: {"row": 0, "type": "circle"},   # Utility: 2.0
        2: {"row": 5, "type": "circle"},   # Major: 5.0
        3: {"row": 0, "type": "diamond"},  # Choice: 10.0
    }
    
    # Each node missing in B
    assert _weighted_distance({1}, {1: 1}, set_b, ranks_b, node_meta) == 2.0
    assert _weighted_distance({2}, {2: 1}, set_b, ranks_b, node_meta) == 5.0
    assert _weighted_distance({3}, {3: 1}, set_b, ranks_b, node_meta) == 10.0


def test_weighted_distance_rank_difference():
    set_a = {1}
    ranks_a = {1: 2}
    set_b = {1}
    ranks_b = {1: 1}
    node_meta = {1: {"row": 0, "type": "circle"}}
    
    # Both have it, rank diff 1 -> 1 * 0.5 = 0.5
    assert _weighted_distance(set_a, ranks_a, set_b, ranks_b, node_meta) == 0.5
    
    # Rank diff 2 -> 2 * 0.5 = 1.0
    assert _weighted_distance({1}, {1: 3}, {1}, {1: 1}, node_meta) == 1.0


def test_weighted_distance_combination():
    # Node 1: Both have it, rank diff 1 (0.5)
    # Node 2: Only A has it, Major (5.0)
    # Node 3: Only B has it, Choice (10.0)
    # Total: 0.5 + 5.0 + 10.0 = 15.5
    set_a = {1, 2}
    ranks_a = {1: 2, 2: 1}
    set_b = {1, 3}
    ranks_b = {1: 1, 3: 1}
    node_meta = {
        1: {"row": 0, "type": "circle"},
        2: {"row": 5, "type": "circle"},
        3: {"row": 0, "type": "diamond"},
    }
    
    assert _weighted_distance(set_a, ranks_a, set_b, ranks_b, node_meta) == 15.5
