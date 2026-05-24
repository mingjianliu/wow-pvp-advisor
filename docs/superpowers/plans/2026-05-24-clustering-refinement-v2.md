# Talent Clustering Refinement V2 Implementation Plan

**Goal:** Further reduce cluster fragmentation while preserving unique "high-tier" variants and ensuring all talent choices are visible.

**Architecture:**
1. **Algorithm Weighting**: 
   - Choice Nodes: 10.0
   - Major Talents (Row 5+): 5.0
   - Utility (Row 1-4): 0.5 (Significantly reduced to prevent utility-driven splits)
   - Rank Differences: 0.1 (Almost ignored unless massive)
   - Threshold: **12.0** (Allows 1 Choice + 4 Utility, or 2 Major + 4 Utility)
2. **Cluster Detail Enrichment**:
   - In `summarize_talent_clusters`, identify nodes that are "Flex within the cluster" (taken by some but not most).
   - Pass these as `flex_takes` to the frontend.
3. **UI Enhancements**:
   - Ensure `app.jsx` correctly shows ALL clusters.
   - Update `Sidebar` or `Tooltip` to show "Internal Cluster Variance" (using `flex_takes`).
   - Fix the "+minor" display issue (ensure it's definitely gone).

---

### Task 1: Refine Weights and Threshold

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Update `_weighted_distance` weights**
```python
        if is_choice:
            weight = 10.0
        elif row >= 5:
            weight = 5.0
        else:
            weight = 0.5 # Utility is now very low weight
```
- [ ] **Step 2: Update rank difference weight to 0.1**
- [ ] **Step 3: Set default threshold to 12.0**

### Task 2: Enrich Cluster Summary with "Internal Flex"

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Calculate `flex_takes` per cluster**
For each cluster, find nodes taken by 10% to 90% of members that aren't already in `takes`.

### Task 3: UI Overhaul for All-Variants

**Files:**
- Modify: `frontend/app.jsx`
- Modify: `frontend/sidebar.jsx`

- [ ] **Step 1: Force `minorCount` to 0 and remove the conditional block**
- [ ] **Step 2: Update Sidebar to list "Internal Flex" nodes**
Show these as "Optional variants in this group".

### Task 4: Validation Loop

- [ ] **Step 1: Generate Rsham, Arms, Hpal reports**
- [ ] **Step 2: Verify cluster counts are reasonable (5-15 per 50 players)**
- [ ] **Step 3: Report to human**
