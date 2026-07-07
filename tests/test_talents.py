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


def test_rank_distribution_normalization_relative_to_pickers():
    # 10 players total. 5 take node 1.
    # Among those 5: 3 take rank 1, 2 take rank 2.
    # Global pick rate is 50%.
    # Rank distribution SHOULD be: [60%, 40%] (among pickers), NOT [30%, 20%].
    node_sets = [{1}] * 5 + [set()] * 5
    node_ranks_list = [{1: 1}] * 3 + [{1: 2}] * 2 + [{}] * 5

    analysis = analyze_talents(node_sets, node_ranks_list=node_ranks_list)

    # Node 1 dist
    dist = analysis.rank_distributions.get(1)
    assert dist == [60.0, 40.0]

    # Verify pick rate is still 0.5
    assert analysis.pick_rates.get(1) == 0.5


def test_hero_talents_excluded_from_skips():
    # Node 100 is Hero node. Node 200 is contested non-hero node.
    # Cluster chooses Hero node 100 but skips 200.
    # In summarize_talent_clusters, hero node 101 (from other tree) should NOT be in skips.
    node_sets = [{100}, {100}]
    node_meta = {
        100: {"is_hero": True, "type": "circle", "row": 0},
        101: {"is_hero": True, "type": "circle", "row": 0},
        200: {"type": "circle", "row": 5},  # Contested
    }
    # Player 3 took 200, making it contested
    full_node_sets = node_sets + [{200}]
    codes = ["A", "B", "C"]

    result = summarize_talent_clusters(full_node_sets, codes, node_meta=node_meta)

    # Cluster 1 (the 2 players taking 100)
    c1 = result["clusters"][0]
    skip_ids = [s["id"] for s in c1["skips"]]

    assert 200 in skip_ids
    assert 101 not in skip_ids


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


def test_calculate_medoid():
    from wow_advisor.processor.talents import _calculate_medoid
    # Create a cluster of 3 members.
    cluster = [
        ({1, 2}, 0),
        ({1, 2, 3}, 1),
        ({10, 11}, 2)
    ]
    node_ranks_list = [
        {1: 1, 2: 1},
        {1: 1, 2: 1, 3: 1},
        {10: 1, 11: 1}
    ]
    node_meta = {
        1: {"row": 0, "type": "circle"},
        2: {"row": 0, "type": "circle"},
        3: {"row": 0, "type": "circle"},
        10: {"row": 0, "type": "circle"},
        11: {"row": 0, "type": "circle"},
    }
    
    medoid_nodes, medoid_idx = _calculate_medoid(cluster, node_ranks_list, node_meta)
    assert medoid_idx in (0, 1)


def test_calculate_silhouette_scores():
    from wow_advisor.processor.talents import calculate_silhouette_scores
    # We have two well-separated clusters:
    # Cluster 0: member 0={1, 2}, member 1={1, 2, 3} (both close to each other)
    # Cluster 1: member 2={10, 11}, member 3={10, 11, 12} (both close to each other, far from Cluster 0)
    clusters = [
        [({1, 2}, 0), ({1, 2, 3}, 1)],
        [({10, 11}, 2), ({10, 11, 12}, 3)]
    ]
    node_ranks_list = [
        {1: 1, 2: 1},
        {1: 1, 2: 1, 3: 1},
        {10: 1, 11: 1},
        {10: 1, 11: 1, 12: 1}
    ]
    node_meta = {
        1: {"row": 0, "type": "circle"},
        2: {"row": 0, "type": "circle"},
        3: {"row": 0, "type": "circle"},
        10: {"row": 0, "type": "circle"},
        11: {"row": 0, "type": "circle"},
        12: {"row": 0, "type": "circle"},
    }
    
    scores = calculate_silhouette_scores(clusters, node_ranks_list, node_meta)
    
    # Points 0 and 1 are in Cluster 0.
    # a(0) = d(0, 1) = 0.333
    # b(0) = mean(d(0, 2), d(0, 3)) = mean(1.0, 1.0) = 1.0
    # s(0) = (1.0 - 0.333) / 1.0 = 0.667
    
    # Points 2 and 3 are in Cluster 1.
    # a(2) = d(2, 3) = 0.333
    # b(2) = mean(d(2, 0), d(2, 1)) = 1.0
    # s(2) = (1.0 - 0.333) / 1.0 = 0.667

    assert scores[0] > 0.5
    assert scores[1] > 0.5
    assert scores[2] > 0.5
    assert scores[3] > 0.5


def test_cluster_talents_hac_average():
    from wow_advisor.processor.talents import cluster_talents_hac_average
    pairs = [
        ({1, 2}, 0),
        ({1, 2, 3}, 1),
        ({10, 11}, 2)
    ]
    node_ranks_list = [
        {1: 1, 2: 1},
        {1: 1, 2: 1, 3: 1},
        {10: 1, 11: 1}
    ]
    node_meta = {
        1: {"row": 0, "type": "circle"},
        2: {"row": 0, "type": "circle"},
        3: {"row": 0, "type": "circle"},
        10: {"row": 0, "type": "circle"},
        11: {"row": 0, "type": "circle"},
    }
    
    clusters = cluster_talents_hac_average(pairs, node_ranks_list, node_meta, threshold=0.4)
    assert len(clusters) == 2
    assert len(clusters[0]) == 2
    assert len(clusters[1]) == 1





def test_hero_partition_same_tree_different_picks():
    # Hero trees contain choice nodes: two players on the SAME tree with
    # different exact picks must land in one partition.
    from wow_advisor.processor.talents import _hero_partition
    node_sets = [{1, 100}, {1, 101}]
    node_meta = {
        100: {"is_hero": True, "hero_tree": "left", "type": "circle", "row": 0},
        101: {"is_hero": True, "hero_tree": "left", "type": "circle", "row": 0},
    }
    groups = _hero_partition(node_sets, {100, 101}, node_meta)
    assert len(groups) == 1
    assert list(groups.values())[0] == [0, 1]


def test_hero_partition_different_trees_split():
    from wow_advisor.processor.talents import _hero_partition
    node_sets = [{1, 100}, {1, 101}]
    node_meta = {
        100: {"is_hero": True, "hero_tree": "left", "type": "circle", "row": 0},
        101: {"is_hero": True, "hero_tree": "right", "type": "circle", "row": 0},
    }
    groups = _hero_partition(node_sets, {100, 101}, node_meta)
    assert len(groups) == 2


def test_hero_partition_falls_back_to_exact_sets_without_side_info():
    # Without "hero_tree" side info, grouping degrades to exact node sets
    # (the pre-fix behavior), so differing hero picks still split.
    from wow_advisor.processor.talents import _hero_partition
    node_sets = [{1, 100}, {1, 101}]
    node_meta = {
        100: {"is_hero": True, "type": "circle", "row": 0},
        101: {"is_hero": True, "type": "circle", "row": 0},
    }
    groups = _hero_partition(node_sets, {100, 101}, node_meta)
    assert len(groups) == 2


def test_hac_uses_original_indices_for_ranks():
    # Regression: HAC must look up node_ranks by the ORIGINAL player index
    # carried in each pair, not by position within the (possibly subset)
    # pairs list. Players 2 and 3 have identical builds and ranks, so they
    # must merge — the buggy positional lookup would read players 0/1's
    # wildly different ranks and split them.
    from wow_advisor.processor.talents import cluster_talents_hac
    node_ranks_list = [{1: 1}, {1: 100}, {1: 1}, {1: 1}]
    pairs = [({1}, 2), ({1}, 3)]
    node_meta = {1: {"row": 0, "type": "circle"}}
    clusters = cluster_talents_hac(pairs, node_ranks_list, node_meta, threshold=0.3)
    assert len(clusters) == 1
