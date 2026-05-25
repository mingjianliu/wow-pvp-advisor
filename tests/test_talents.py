import pytest
from wow_advisor.processor.talents import (
    analyze_talents,
    cluster_talents,
    summarize_talent_clusters,
    _weighted_jaccard_distance,
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
    # 5 players take node 100, 5 take node 101 — distance = 1.0, threshold = 0.5 → 2 clusters
    pairs = [({100}, i) for i in range(5)] + [({101}, i + 5) for i in range(5)]
    node_ranks = [{} for _ in range(10)]
    node_meta = {}
    clusters = cluster_talents(pairs, node_ranks, node_meta, threshold=0.5)
    assert len(clusters) == 2
    assert sorted(len(c) for c in clusters) == [5, 5]


def test_cluster_merges_near_identical():
    # {100} vs {100, 101} differ by 1 node.
    # Node 100, 101 are utility (0.1 weight)
    # Int = 0.1, Union = 0.2 -> Dist = 0.5. Within threshold=0.6 → 1 cluster
    pairs = [({100}, i) for i in range(5)] + [({100, 101}, i + 5) for i in range(5)]
    node_ranks = [{} for _ in range(10)]
    node_meta = {}
    clusters = cluster_talents(pairs, node_ranks, node_meta, threshold=0.6)
    assert len(clusters) == 1


def test_cluster_sorted_by_size_descending():
    # 7 players take {100}, 3 take {101}
    pairs = [({100}, i) for i in range(7)] + [({101}, i + 7) for i in range(3)]
    node_ranks = [{} for _ in range(10)]
    node_meta = {}
    clusters = cluster_talents(pairs, node_ranks, node_meta, threshold=0.5)
    assert len(clusters[0]) >= len(clusters[1])


def test_full_pipeline_two_builds():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(7)), 11: list(range(7, 10))})
    node_ranks = [{} for _ in range(10)]
    node_meta = {10: {"row": 5}, 11: {"row": 5}}  # Major node
    # Dist will be 1.0 if they take different majors. Threshold 0.5 -> split.
    pairs = [(node_sets[i], i) for i in range(10)]
    clusters = cluster_talents(pairs, node_ranks, node_meta, threshold=0.5)
    assert len(clusters) == 2
    sizes = sorted([len(c) for c in clusters], reverse=True)
    assert sizes == [7, 3]


def test_summarize_returns_expected_shape():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(7)), 11: list(range(7, 10))})
    node_meta = {10: {"row": 5, "type": "diamond"}, 11: {"row": 5, "type": "diamond"}}
    codes = [f"code_{i}" for i in range(10)]
    # We need to ensure threshold in summarize_talent_clusters is also updated or these will merge.
    result = summarize_talent_clusters(node_sets, codes, node_meta=node_meta)
    assert "core_nodes" in result
    assert "contested_nodes" in result
    assert "clusters" in result
    assert result["clustering_method"] == "variance+weighted"
    # If threshold is still 30.0, this will be 1 cluster.
    # I will update the production code threshold next.
    assert len(result["clusters"]) == 2
    assert result["clusters"][0]["pct"] == 70.0


def test_hero_tree_split():
    # Build A has Hero Node 100, Build B has Hero Node 101.
    # Even if they are otherwise identical, they must split because of partitioning.
    node_sets = [{1, 100}, {1, 101}]
    node_meta = {
        100: {"is_hero": True, "type": "circle", "row": 0},
        101: {"is_hero": True, "type": "circle", "row": 0},
    }
    codes = ["code_A", "code_B"]
    result = summarize_talent_clusters(node_sets, codes, node_meta=node_meta)
    
    # Should split into 2 clusters because they are in different hero groups
    assert len(result["clusters"]) == 2


def test_rank_shuffle_merge():
    # Two builds with multiple 1/2 vs 2/2 swaps.
    # Utility nodes (0.1 weight). Rank diff 1 -> dist 0.1. 3 nodes -> Int=0.27, Union=0.3 -> Dist=0.1.
    # Threshold 0.2 -> merge.
    node_sets = [{1, 2, 3}, {1, 2, 3}]
    node_ranks_list = [
        {1: 1, 2: 1, 3: 1},
        {1: 2, 2: 2, 3: 2}
    ]
    node_meta = {
        1: {"row": 0}, 2: {"row": 0}, 3: {"row": 0}
    }
    pairs = [(node_sets[i], i) for i in range(2)]
    clusters = cluster_talents(pairs, node_ranks_list, node_meta, threshold=0.2)
    assert len(clusters) == 1


def test_choice_node_split():
    # Swapping one choice node (20.0 weight) should force a split (threshold 0.5)
    # Int=0.1 (node 1), Union=20.1 -> Dist = 1 - 0.1/20.1 ≈ 0.995
    node_sets = [{1, 10}, {1, 11}]
    node_meta = {
        1: {"row": 0, "type": "circle"},
        10: {"type": "diamond", "row": 0},
        11: {"type": "diamond", "row": 0}
    }
    node_ranks = [{} for _ in range(2)]
    pairs = [(node_sets[i], i) for i in range(2)]
    clusters = cluster_talents(pairs, node_ranks, node_meta, threshold=0.5)
    assert len(clusters) == 2


def test_analyze_includes_node_meta():
    node_sets = [{1}]
    node_meta = {1: {"row": 0, "type": "circle"}}
    analysis = analyze_talents(node_sets, node_meta=node_meta)
    assert analysis.node_meta == node_meta
def test_weighted_jaccard_distance_basic():
    set_a = {1}
    ranks_a = {1: 1}
    set_b = set()
    ranks_b = {}
    node_meta = {1: {"row": 0, "type": "circle"}}  # Utility node
    
    # Distance should be 1.0 for single node difference in Jaccard
    assert _weighted_jaccard_distance(set_a, ranks_a, set_b, ranks_b, node_meta) == 1.0


def test_weighted_jaccard_distance_node_types():
    set_b = set()
    ranks_b = {}
    
    # Missing node always results in distance 1.0 in Jaccard
    assert _weighted_jaccard_distance({1}, {1: 1}, set_b, ranks_b, {1: {"row": 0, "type": "circle"}}) == 1.0
    assert _weighted_jaccard_distance({1}, {1: 1}, set_b, ranks_b, {1: {"row": 5, "type": "circle"}}) == 1.0
    assert _weighted_jaccard_distance({1}, {1: 1}, set_b, ranks_b, {1: {"row": 0, "type": "diamond"}}) == 1.0


def test_weighted_jaccard_distance_rank_difference():
    set_a = {1}
    ranks_a = {1: 2}
    set_b = {1}
    ranks_b = {1: 1}
    node_meta = {1: {"row": 0, "type": "circle"}} # weight 0.1
    
    # Both have it, rank diff 1 -> Int = 0.1 - 0.01 = 0.09. Union = 0.1. Dist = 1 - 0.9 = 0.1
    assert pytest.approx(_weighted_jaccard_distance(set_a, ranks_a, set_b, ranks_b, node_meta)) == 0.1
    
    # Rank diff 2 -> Int = 0.1 - 0.02 = 0.08. Union = 0.1. Dist = 0.2
    assert pytest.approx(_weighted_jaccard_distance({1}, {1: 3}, {1}, {1: 1}, node_meta)) == 0.2


def test_weighted_jaccard_distance_combination():
    # Node 1: Choice (20.0), both have, rank diff 1 -> Int=19.99, Union=20.0
    # Node 2: Major (5.0), only A has -> Int=0, Union=5.0
    # Node 3: Choice (20.0), only B has -> Int=0, Union=20.0
    # Total Int = 19.99
    # Total Union = 20.0 + 5.0 + 20.0 = 45.0
    # Distance = 1 - 19.99 / 45.0 = 25.01 / 45.0 ≈ 0.55577
    set_a = {1, 2}
    ranks_a = {1: 2, 2: 1}
    set_b = {1, 3}
    ranks_b = {1: 1, 3: 1}
    node_meta = {
        1: {"row": 0, "type": "diamond"},
        2: {"row": 5, "type": "circle"},
        3: {"row": 0, "type": "diamond"},
    }
    
    assert pytest.approx(_weighted_jaccard_distance(set_a, ranks_a, set_b, ranks_b, node_meta)) == 25.01 / 45.0
