from wow_advisor.processor.talents import cluster_talents_hac

def test_hac_clustering_basic():
    # Mock data: pairs of (set(talent_ids), original_index)
    # Build A and B are close, Build C is far
    build_a = ({1, 2, 3}, 0)
    build_b = ({1, 2, 4}, 1)
    build_c = ({10, 11, 12}, 2)
    
    pairs = [build_a, build_b, build_c]
    
    # We need a mock node_ranks_list and node_meta for weighted Jaccard
    node_ranks_list = [
        {1: 1, 2: 1, 3: 1}, # A
        {1: 1, 2: 1, 4: 1}, # B
        {10: 1, 11: 1, 12: 1} # C
    ]
    node_meta = {
        1: {"type": "circle", "row": 1}, 2: {"type": "circle", "row": 2}, 3: {"type": "circle", "row": 3}, 
        4: {"type": "circle", "row": 3},
        10: {"type": "circle", "row": 1}, 11: {"type": "circle", "row": 2}, 12: {"type": "circle", "row": 3}
    }
    
    # Run HAC with a threshold that should group A and B but keep C separate.
    # Weighted Jaccard: 
    # A vs B: 
    # shared: 1 (row 1), 2 (row 2)
    # only A: 3 (row 3)
    # only B: 4 (row 3)
    # weights: row < 5 => 0.1
    # intersection = 0.1 + 0.1 = 0.2
    # union = 0.1 (1) + 0.1 (2) + 0.1 (3) + 0.1 (4) = 0.4
    # dist = 1 - (0.2 / 0.4) = 0.5
    
    # Wait, my threshold in the test was 0.3, but 0.5 > 0.3.
    # Let's adjust the mock data or threshold.
    # If I make 1 and 2 "Major" nodes (row >= 5):
    # weights: 1: 5.0, 2: 5.0, 3: 0.1, 4: 0.1
    # intersection = 5.0 + 5.0 = 10.0
    # union = 5.0 + 5.0 + 0.1 + 0.1 = 10.2
    # dist = 1 - (10.0 / 10.2) = 1 - 0.98 = 0.02
    
    node_meta = {
        1: {"type": "circle", "row": 5}, 2: {"type": "circle", "row": 6}, 3: {"type": "circle", "row": 1}, 
        4: {"type": "circle", "row": 1},
        10: {"type": "circle", "row": 5}, 11: {"type": "circle", "row": 6}, 12: {"type": "circle", "row": 1}
    }
    
    # Run HAC
    clusters = cluster_talents_hac(pairs, node_ranks_list, node_meta, threshold=0.3)
    
    # Expected: A and B in one cluster, C in another
    assert len(clusters) == 2
    
    # Check if A and B are in the same cluster
    found_ab = False
    for cluster in clusters:
        members = [p[0] for p in cluster]
        if {1, 2, 3} in members and {1, 2, 4} in members:
            found_ab = True
            assert len(cluster) == 2
    assert found_ab
