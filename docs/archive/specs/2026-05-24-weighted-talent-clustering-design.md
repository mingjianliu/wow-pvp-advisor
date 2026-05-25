# Design Spec: Weighted Structural Talent Clustering

## Overview
The current talent clustering algorithm uses simple Hamming distance on a limited set of "contested" nodes. This leads to fragmented clusters where minor point shuffles (e.g., 1/2 vs 2/2 in a utility node) create distinct clusters, while major playstyle markers (like Hero Talent choices) are treated with equal weight to utility nodes.

This design introduces **Weighted Structural Clustering**, which partitions builds by Hero Tree first and then uses a weighted distance metric to group builds by meaningful gameplay decisions.

## Objectives
- **Eliminate Noise**: Merge builds that differ only by minor utility or rank-distribution choices.
- **Preserve Playstyles**: Ensure builds with different Hero Trees or major "Choice" nodes are always separated.
- **Scale Automatically**: Use tree-row data to weigh nodes without requiring manual per-spec "keystone" lists (though keeping overrides as a fallback).

## Proposed Architecture

### 1. Two-Phase Partitioning
1.  **Phase 1: Hard Split by Hero Tree**: 
    - Identify the Hero Tree selected by each build.
    - Group builds into buckets by Hero Tree ID.
    - Clustering logic only runs *within* each bucket.
2.  **Phase 2: Weighted Hamming Clustering**:
    - Within each bucket, calculate the **Weighted Distance** between builds.
    - Use a greedy clustering algorithm with a fixed distance threshold.

### 2. Weighting Model
Weights are assigned based on the node's position and type in the tree:

| Feature | Weight | Trigger |
| :--- | :--- | :--- |
| **Hero Tree** | ∞ | Any difference in Hero Tree ID forces a split. |
| **Choice Node (2-in-1)** | 10.0 | Selection of a different option in a choice node. |
| **Major Node (Row 5-10)** | 5.0 | Taking vs. Skipping a node in the bottom half of the tree. |
| **Utility Node (Row 1-4)** | 2.0 | Taking vs. Skipping a node in the top half of the tree. |
| **Rank Variance** | 0.5 | Difference in ranks (e.g. 1/2 vs 2/2) for a node taken by both. |

### 3. Clustering Logic
- **Similarity Metric**: `Weighted Distance(A, B) = Σ Weight(node) * Diff(A, B)`
- **Threshold**: **5.0**
    - A single major node difference (5.0) or Choice Node difference (10.0) triggers a new cluster.
    - Up to 2 minor utility differences (2 * 2.0 = 4.0) or 10 rank shuffles (10 * 0.5 = 5.0) are allowed within the same cluster.

## Implementation Details

### Data Processing Changes
- `TalentAnalysis` should now include `row` information for every node (available from `get_tree_structure`).
- `summarize_talent_clusters` will be refactored to support partitioned clustering.
- `cluster_talents` will be updated to accept a weight-aware distance function instead of simple `set.symmetric_difference`.

### Expected Impact
- **Reduced Fragmentation**: Total clusters per spec/bracket should drop by 30-50%.
- **Cleaner "Major" Clusters**: The "Top" clusters will represent more distinct, recognizable builds.
- **Better Canonical Codes**: Canonical codes will represent the "modal" build of a larger group of players.

## Verification Plan
1.  **Unit Tests**: Update `tests/test_talents.py` with cases for:
    - Hero tree partitioning.
    - Major vs Minor weighting.
    - Rank variance merging.
2.  **Regression Check**: Run the CLI `report` tool on a diverse spec (e.g., Resto Shaman) to visually verify cluster quality.
