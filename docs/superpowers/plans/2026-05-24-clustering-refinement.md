# Clustering Refinement Implementation Plan

**Goal:** Reduce cluster fragmentation by increasing the similarity threshold and ensure all build variants (including N=1) are visible in the UI.

**Architecture:**
1. **Algorithm Update**: Increase `threshold` to 10.0 (requires two major node differences or one choice node difference to split).
2. **UI Update**: Remove the filter that hides clusters with `count < 2`. Label them appropriately.
3. **Multi-Spec Validation**: Run reports for multiple specs to ensure the changes improve results across the board.

---

### Task 1: Update Clustering Threshold

**Files:**
- Modify: `wow_advisor/processor/talents.py`

- [ ] **Step 1: Change default threshold**
Increase `threshold` from 5.0 to 10.0 in `cluster_talents` and `summarize_talent_clusters`.

- [ ] **Step 2: Update tests**
Adjust `tests/test_talents.py` expectations to match the new threshold.

### Task 2: Show All Clusters in UI

**Files:**
- Modify: `frontend/app.jsx`

- [ ] **Step 1: Remove cluster filtering**
Show all clusters regardless of player count.

- [ ] **Step 2: Update UI labels**
Maybe add a visual indicator for "Unique Build" or "Rare Variant" for N=1 clusters.

### Task 3: Multi-Spec Review & Report

**Files:**
- Action: Run `python cli.py fetch` and `build_page` for 3-4 diverse specs.
- Action: Report results to user.
