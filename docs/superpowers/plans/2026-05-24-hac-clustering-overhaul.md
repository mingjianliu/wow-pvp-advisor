# HAC Algorithm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the greedy talent clustering with Agglomerative Hierarchical Clustering (HAC) using Complete Linkage for more stable and accurate meta-build discovery.

**Architecture:** Use a pure-Python HAC implementation that merges the most similar clusters (minimum distance) until a distance threshold is reached. Complete Linkage ensures that the distance between clusters is defined by the maximum distance between any two members, preventing "chaining" and favoring compact, well-separated clusters.

**Tech Stack:** Python 3.12+, `wow_advisor` internal processor.

---

### Task 1: Research and Test Setup

**Files:**
- Modify: `wow_advisor/processor/talents.py`
- Create: `tests/test_hac_clustering.py`

- [ ] **Step 1: Research current implementation**

I'll read `wow_advisor/processor/talents.py` to understand the current `cluster_talents` function and how it's called.

- [ ] **Step 2: Create a failing test for HAC clustering**

I'll create a test file that exercises the new `cluster_talents_hac` function (which doesn't exist yet).

```python
import pytest
from wow_advisor.processor.talents import cluster_talents_hac

def test_hac_clustering_basic():
    # Mock data: pairs of (set(talent_ids), count)
    # Build A and B are close, Build C is far
    build_a = ({1, 2, 3}, 10)
    build_b = ({1, 2, 4}, 5)
    build_c = ({10, 11, 12}, 8)
    
    pairs = [build_a, build_b, build_c]
    
    # We need a mock node_ranks_list and node_meta for weighted Jaccard
    node_ranks_list = [
        {1: 1, 2: 1, 3: 1}, # A
        {1: 1, 2: 1, 4: 1}, # B
        {10: 1, 11: 1, 12: 1} # C
    ]
    node_meta = {
        1: {"type": "class"}, 2: {"type": "spec"}, 3: {"type": "spec"}, 4: {"type": "spec"},
        10: {"type": "spec"}, 11: {"type": "spec"}, 12: {"type": "spec"}
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hac_clustering.py -v`
Expected: FAIL with `ImportError: cannot import name 'cluster_talents_hac' from 'wow_advisor.processor.talents'`

### Task 2: Implement HAC Algorithm

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Implement `cluster_talents_hac` function**

I'll add the `cluster_talents_hac` function to `wow_advisor/processor/talents.py`.

```python
def cluster_talents_hac(
    pairs: list[tuple[set[int], int]],
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = 0.3,
) -> list[list[tuple[set[int], int]]]:
    """
    Cluster talent builds using Agglomerative Hierarchical Clustering (HAC)
    with Complete Linkage and Weighted Jaccard Distance.
    """
    if not pairs:
        return []

    # Every point starts as its own cluster (a list containing one pair and its original index)
    # We store (pair, original_index) to look up node_ranks
    clusters = [[(pairs[i], i)] for i in range(len(pairs))]
    
    while len(clusters) > 1:
        best_dist = float('inf')
        best_pair = (None, None)
        
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Complete Linkage: max distance between all members of clusters
                max_d = 0.0
                for (p_a, idx_a) in clusters[i]:
                    for (p_b, idx_b) in clusters[j]:
                        d = _weighted_jaccard_distance(
                            p_a[0], node_ranks_list[idx_a],
                            p_b[0], node_ranks_list[idx_b],
                            node_meta
                        )
                        if d > max_d:
                            max_d = d
                            # Optimization: if max_d already exceeds current best_dist, 
                            # we can stop checking this cluster pair
                            if max_d >= best_dist:
                                break
                    if max_d >= best_dist:
                        break
                
                if max_d < best_dist:
                    best_dist = max_d
                    best_pair = (i, j)
        
        if best_dist > threshold:
            break
            
        i, j = best_pair
        clusters[i].extend(clusters[j])
        clusters.pop(j)
        
    # Unwrap (pair, index) back to just pair for the return value
    final_clusters = []
    for c in clusters:
        final_clusters.append([p for p, idx in c])
        
    return sorted(final_clusters, key=len, reverse=True)
```

- [ ] **Step 2: Run tests to verify it passes**

Run: `pytest tests/test_hac_clustering.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add wow_advisor/processor/talents.py tests/test_hac_clustering.py
git commit -m "feat: implement HAC clustering with Complete Linkage"
```

### Task 3: Update `summarize_talent_clusters` and Integration

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Replace old clustering with HAC in `summarize_talent_clusters`**

I'll update `summarize_talent_clusters` to use `cluster_talents_hac`.

- [ ] **Step 2: Run existing talent tests**

Run: `pytest tests/test_talents.py tests/test_summary.py -v`
Expected: PASS (or minimal adjustments if tests were sensitive to exact cluster contents)

- [ ] **Step 3: Commit**

```bash
git add wow_advisor/processor/talents.py
git commit -m "refactor: use HAC clustering in summarize_talent_clusters"
```
