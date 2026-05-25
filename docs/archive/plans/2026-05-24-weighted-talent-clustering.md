# Weighted Structural Talent Clustering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a weighted clustering algorithm that groups talent builds by meaningful gameplay decisions (Hero Tree, Choice nodes, major talents) while ignoring minor utility noise.

**Architecture:** 
1. **Partitioning**: Split builds by Hero Tree selection first.
2. **Weighted Hamming Distance**: Calculate similarity using weights based on tree position and node type.
3. **Refactored Clustering**: Update the pipeline to use these weights and a higher threshold to reduce fragmentation.

**Tech Stack:** Python, Dataclasses, Counter

---

### Task 1: Enhance Talent Metadata

**Files:**
- Modify: `wow_advisor/processor/talents.py`
- Modify: `wow_advisor/processor/aggregator.py`
- Test: `tests/test_talents.py`

- [ ] **Step 1: Update `TalentAnalysis` dataclass**
Add `node_meta` to store row and type info.

```python
@dataclass
class TalentAnalysis:
    core_nodes: set[int] = field(default_factory=set)
    flex_nodes: set[int] = field(default_factory=set)
    contested_nodes: set[int] = field(default_factory=set)
    pick_rates: dict[int, float] = field(default_factory=dict)
    rank_distributions: dict[int, list[float]] = field(default_factory=dict)
    node_meta: dict[int, dict] = field(default_factory=dict) # NEW: {node_id: {"row": int, "type": str}}
```

- [ ] **Step 2: Update `analyze_talents` to accept node metadata**
Update the signature to accept `node_meta`.

- [ ] **Step 3: Update `summarize_talent_clusters` signature**
Add `node_meta` parameter.

- [ ] **Step 4: Update `build_aggregation` in `aggregator.py`**
Fetch tree structure and extract node metadata to pass to `summarize_talent_clusters`.

- [ ] **Step 5: Commit**
`git add wow_advisor/processor/talents.py wow_advisor/processor/aggregator.py && git commit -m "feat: add node metadata support to talent analysis"`

### Task 2: Implement Weighted Hamming Distance

**Files:**
- Modify: `wow_advisor/processor/talents.py`
- Test: `tests/test_talents.py`

- [ ] **Step 1: Write `_weighted_distance` function**
Implement the logic based on the design spec.

```python
def _weighted_distance(
    set_a: set[int], 
    ranks_a: dict[int, int],
    set_b: set[int], 
    ranks_b: dict[int, int],
    node_meta: dict[int, dict]
) -> float:
    all_nodes = set_a | set_b
    distance = 0.0
    
    for nid in all_nodes:
        meta = node_meta.get(nid, {"row": 0, "type": "circle"})
        row = meta.get("row", 0)
        is_choice = meta.get("type") == "diamond"
        
        # Base weight by row/type
        if is_choice:
            weight = 10.0
        elif row >= 5: # Apex (8-10) and Key (5-7)
            weight = 5.0
        else: # Utility (1-4)
            weight = 2.0
            
        in_a = nid in set_a
        in_b = nid in set_b
        
        if in_a != in_b:
            # One build has it, other doesn't
            distance += weight
        elif in_a and in_b:
            # Both have it, check rank difference
            rank_a = ranks_a.get(nid, 1)
            rank_b = ranks_b.get(nid, 1)
            if rank_a != rank_b:
                distance += abs(rank_a - rank_b) * 0.5
                
    return distance
```

- [ ] **Step 2: Add unit tests for `_weighted_distance`**
Verify that choice nodes and presence/absence weigh more than rank swaps.

- [ ] **Step 3: Commit**
`git add wow_advisor/processor/talents.py tests/test_talents.py && git commit -m "feat: implement weighted distance function"`

### Task 3: Implement Hero Tree Partitioning

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Add `hero_tree_map` to `summarize_talent_clusters`**
Identify which builds belong to which Hero Tree.

- [ ] **Step 2: Update `cluster_talents` to support weights and custom threshold**
Refactor to accept weights and the new 5.0 threshold.

- [ ] **Step 3: Update `summarize_talent_clusters` to loop over Hero Tree buckets**
Perform clustering independently for each Hero Tree.

- [ ] **Step 4: Commit**
`git add wow_advisor/processor/talents.py && git commit -m "feat: implement hero tree partitioning and weighted clustering"`

### Task 4: Verification and Cleanup

**Files:**
- Test: `tests/test_talents.py`

- [ ] **Step 1: Add full pipeline tests**
Test with synthetic builds that should be merged (rank shuffles) vs. split (hero tree or choice node).

- [ ] **Step 2: Run all tests**
`pytest tests/test_talents.py`

- [ ] **Step 3: Final Commit**
`git add tests/test_talents.py && git commit -m "test: verify weighted clustering pipeline"`
