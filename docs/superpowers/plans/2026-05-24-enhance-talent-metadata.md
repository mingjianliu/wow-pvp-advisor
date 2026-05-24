# Enhance Talent Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store and pass node metadata (row and type) through the talent analysis pipeline to support weighted talent clustering.

**Architecture:** Update `TalentAnalysis` dataclass to include `node_meta`. Update pipeline functions (`analyze_talents`, `summarize_talent_clusters`) to accept and use this metadata. Update `build_aggregation` to fetch this metadata from the talent tree structure.

**Tech Stack:** Python, Dataclasses, Pytest.

---

### Task 1: Update TalentAnalysis Dataclass and analyze_talents

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Update TalentAnalysis dataclass**

Add `node_meta: dict[int, dict] = field(default_factory=dict)` to the `TalentAnalysis` dataclass.

```python
@dataclass
class TalentAnalysis:
    core_nodes: set[int] = field(default_factory=set)
    flex_nodes: set[int] = field(default_factory=set)
    contested_nodes: set[int] = field(default_factory=set)
    pick_rates: dict[int, float] = field(default_factory=dict)
    rank_distributions: dict[int, list[float]] = field(default_factory=dict)
    node_meta: dict[int, dict] = field(default_factory=dict) # NEW
```

- [ ] **Step 2: Update analyze_talents signature**

Update `analyze_talents` to accept `node_meta: dict[int, dict] | None = None`. Pass it to the `TalentAnalysis` constructor.

```python
def analyze_talents(
    node_sets: list[set[int]],
    node_ranks_list: list[dict[int, int]] | None = None,
    core_threshold: float = 0.8,
    flex_threshold: float = 0.2,
    node_meta: dict[int, dict] | None = None, # NEW
) -> TalentAnalysis:
    # ... existing code ...
    return TalentAnalysis(
        core_nodes=core,
        flex_nodes=flex,
        contested_nodes=contested,
        pick_rates=pick_rates,
        rank_distributions=rank_distributions,
        node_meta=node_meta or {}, # NEW
    )
```

- [ ] **Step 3: Update summarize_talent_clusters signature**

Update `summarize_talent_clusters` to accept `node_meta: dict[int, dict] | None = None`. Pass it to `analyze_talents`.

```python
def summarize_talent_clusters(
    node_sets: list[set[int]],
    loadout_codes: list[str],
    keystone_nodes: list[int] | None = None,
    node_ranks_list: list[dict[int, int]] | None = None,
    node_meta: dict[int, dict] | None = None, # NEW
) -> dict:
    # ...
    analysis = analyze_talents(node_sets, node_ranks_list=node_ranks_list, node_meta=node_meta)
    # ...
```

### Task 2: Update build_aggregation in aggregator.py

**Files:**
- Modify: `wow_advisor/processor/aggregator.py`

- [ ] **Step 1: Fetch and extract node metadata**

In `build_aggregation`, fetch the tree structure and extract node metadata.

```python
from wow_advisor.talent_tree import get_tree_structure

def build_aggregation(...):
    # ...
    # Fetch tree structure to get node metadata (row, type)
    tree_data = get_tree_structure(spec)
    node_meta = {}
    if "error" not in tree_data:
        # Extract from main trees (class, spec)
        for tree in tree_data.get("trees", []):
            for node in tree.get("nodes", []):
                node_meta[node["id"]] = {"row": node["row"], "type": node["type"]}
        # Extract from hero trees
        for side in ["left", "right"]:
            hero_tree = tree_data.get("heroTrees", {}).get(side, {})
            for node in hero_tree.get("nodes", []):
                node_meta[node["id"]] = {"row": node["row"], "type": node["type"]}
    
    talent_summary = summarize_talent_clusters(
        node_sets=node_sets,
        loadout_codes=loadout_codes,
        keystone_nodes=keystone_nodes,
        node_ranks_list=node_ranks_list,
        node_meta=node_meta, # PASS HERE
    )
    # ...
```

### Task 3: Update Tests

**Files:**
- Modify: `tests/test_talents.py`

- [ ] **Step 1: Update existing tests for TalentAnalysis**

Update any tests that might fail due to the new field in `TalentAnalysis` if they check the whole object or constructor. (Existing tests seem fine as they check specific fields, but `analyze_talents` signature changed).

- [ ] **Step 2: Add test for node_meta passing**

Add a test case to verify `node_meta` is correctly stored in `TalentAnalysis`.

```python
def test_analyze_includes_node_meta():
    node_sets = [{1}]
    node_meta = {1: {"row": 0, "type": "circle"}}
    analysis = analyze_talents(node_sets, node_meta=node_meta)
    assert analysis.node_meta == node_meta
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/test_talents.py`
Expected: PASS
