import pytest
from wow_advisor.processor.talents import _weighted_jaccard_distance

def test_weighted_jaccard_distance_basic():
    # Identical sets
    set_a = {1}
    ranks_a = {1: 1}
    set_b = {1}
    ranks_b = {1: 1}
    node_meta = {1: {"row": 0, "type": "circle"}} # Utility: 0.1
    
    # Intersection = 0.1, Union = 0.1 -> Distance = 1 - 0.1/0.1 = 0
    assert _weighted_jaccard_distance(set_a, ranks_a, set_b, ranks_b, node_meta) == 0.0

def test_weighted_jaccard_distance_completely_different():
    set_a = {1}
    ranks_a = {1: 1}
    set_b = {2}
    ranks_b = {2: 1}
    node_meta = {
        1: {"row": 0, "type": "circle"}, # Utility: 0.1
        2: {"row": 0, "type": "circle"}  # Utility: 0.1
    }
    
    # Intersection = 0, Union = 0.1 + 0.1 = 0.2 -> Distance = 1 - 0/0.2 = 1.0
    assert _weighted_jaccard_distance(set_a, ranks_a, set_b, ranks_b, node_meta) == 1.0

def test_weighted_jaccard_distance_weights():
    # Choice node: 20.0
    node_meta = {1: {"row": 0, "type": "diamond"}}
    assert _weighted_jaccard_distance({1}, {1: 1}, set(), {}, node_meta) == 1.0
    
    # Major node: 5.0
    node_meta = {1: {"row": 5, "type": "circle"}}
    assert _weighted_jaccard_distance({1}, {1: 1}, set(), {}, node_meta) == 1.0
    
    # Utility node: 0.1
    node_meta = {1: {"row": 0, "type": "circle"}}
    assert _weighted_jaccard_distance({1}, {1: 1}, set(), {}, node_meta) == 1.0

def test_weighted_jaccard_distance_rank_diff():
    # Choice node: 20.0
    # Both have it, rank diff 1 -> intersection = 20.0 - 0.01 = 19.99
    # Union = 20.0
    # Distance = 1 - 19.99 / 20.0 = 0.01 / 20.0 = 0.0005
    node_meta = {1: {"row": 0, "type": "diamond"}}
    dist = _weighted_jaccard_distance({1}, {1: 1}, {1}, {1: 2}, node_meta)
    assert pytest.approx(dist) == 0.0005

def test_weighted_jaccard_distance_combination():
    # Node 1: Choice (20.0), both have, rank diff 0 -> Int=20.0, Union=20.0
    # Node 2: Major (5.0), only A has -> Int=0, Union=5.0
    # Node 3: Utility (0.1), only B has -> Int=0, Union=0.1
    # Total Int = 20.0
    # Total Union = 20.0 + 5.0 + 0.1 = 25.1
    # Distance = 1 - 20.0 / 25.1 = 5.1 / 25.1 ≈ 0.20318725
    node_meta = {
        1: {"row": 0, "type": "diamond"},
        2: {"row": 5, "type": "circle"},
        3: {"row": 0, "type": "circle"}
    }
    set_a = {1, 2}
    ranks_a = {1: 1, 2: 1}
    set_b = {1, 3}
    ranks_b = {1: 1, 3: 1}
    dist = _weighted_jaccard_distance(set_a, ranks_a, set_b, ranks_b, node_meta)
    assert pytest.approx(dist) == 5.1 / 25.1


def test_weighted_jaccard_distance_entropy():
    # Node 1: Choice (20.0), both have, rank diff 1.
    # pick_rate = 0.5 -> weight = 20.0. Intersection = 20.0 - 0.01 = 19.99. Union = 20.0. Dist = 0.0005
    # pick_rate = 0.99 -> weight = 20.0 * 0.0396 = 0.792. Intersection = 0.792 - 0.01 = 0.782. Union = 0.792. Dist = 0.01 / 0.792 ≈ 0.0126
    node_meta = {
        1: {"row": 0, "type": "diamond"},
    }
    # No pick rates
    dist_no_rates = _weighted_jaccard_distance({1}, {1: 1}, {1}, {1: 2}, node_meta)
    assert pytest.approx(dist_no_rates) == 0.0005

    # Pick rate 0.5 (scale factor 1.0)
    dist_rate_half = _weighted_jaccard_distance({1}, {1: 1}, {1}, {1: 2}, node_meta, pick_rates={1: 0.5})
    assert pytest.approx(dist_rate_half) == 0.0005

    # Pick rate 0.99 (highly uniform, scaled down weight, so rank diff is relatively larger fraction of distance)
    dist_rate_edge = _weighted_jaccard_distance({1}, {1: 1}, {1}, {1: 2}, node_meta, pick_rates={1: 0.99})
    assert pytest.approx(dist_rate_edge) == 0.01 / (20.0 * 4.0 * 0.99 * 0.01)

