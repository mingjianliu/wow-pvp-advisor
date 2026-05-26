import sys
import os

# Ensure we import from the worktree
sys.path.insert(0, "/Users/mingjianliu/code/wow-talent-gear-collector/.worktrees/cluster")

from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.talent_tree import get_tree_structure
from wow_advisor.processor.talents import _weighted_jaccard_distance, calculate_silhouette_scores

def cluster_talents_hac_average(
    pairs, node_ranks_list, node_meta, threshold=0.3, pick_rates=None
):
    """HAC using Average Linkage."""
    if not pairs:
        return []
    clusters = [[(pairs[i], i)] for i in range(len(pairs))]
    
    while len(clusters) > 1:
        best_dist = float('inf')
        best_pair = (None, None)
        
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Average Linkage: average distance between all pairs
                total_d = 0.0
                count = 0
                for (p_a, idx_a) in clusters[i]:
                    for (p_b, idx_b) in clusters[j]:
                        d = _weighted_jaccard_distance(
                            p_a[0], node_ranks_list[idx_a],
                            p_b[0], node_ranks_list[idx_b],
                            node_meta,
                            pick_rates=pick_rates,
                        )
                        total_d += d
                        count += 1
                avg_d = total_d / count if count > 0 else 0.0
                if avg_d < best_dist:
                    best_dist = avg_d
                    best_pair = (i, j)
        
        if best_dist > threshold:
            break
            
        i, j = best_pair
        clusters[i].extend(clusters[j])
        clusters.pop(j)
        
    final_clusters = []
    for c in clusters:
        final_clusters.append([p for p, idx in c])
    return sorted(final_clusters, key=len, reverse=True)

def test_linkage_comparison():
    store = CacheStore(get_default_db())
    conn = get_default_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT spec FROM aggregations")
    specs = [r[0] for r in cursor.fetchall()]
    
    print("| Spec | Complete Linkage (Clusters / Sil) | Average Linkage (Clusters / Sil) | Recommendation |")
    print("|---|---|---|---|")
    
    # Import complete linkage implementation from worktree
    from wow_advisor.processor.talents import cluster_talents_hac, analyze_talents
    
    for spec in specs:
        players = store.get_players(spec, "3v3", "us")
        if not players:
            continue
        players_with_talent = [p for p in players if p.talent]
        if not players_with_talent:
            continue
            
        node_sets = [set(p.talent.all_node_ids) for p in players_with_talent]
        node_ranks_list = [p.talent.node_ranks for p in players_with_talent]
        
        # Get metadata
        tree_data = get_tree_structure(spec)
        node_meta = {}
        if "error" not in tree_data:
            for tree in tree_data.get("trees", []):
                for node in tree.get("nodes", []):
                    node_meta[node["id"]] = {"row": node["row"], "type": node["type"], "is_hero": False}
            hero_trees = tree_data.get("heroTrees", {})
            for side in ["left", "right"]:
                hero_tree = hero_trees.get(side, {})
                for node in hero_tree.get("nodes", []):
                    node_meta[node["id"]] = {"row": node["row"], "type": node["type"], "is_hero": True}
        
        analysis = analyze_talents(node_sets, node_ranks_list=node_ranks_list, node_meta=node_meta)
        
        # Partition by hero trees
        hero_nodes = {nid for nid, meta in node_meta.items() if meta.get("is_hero")}
        hero_groups = {}
        for i in range(len(node_sets)):
            h_set = frozenset(node_sets[i] & hero_nodes)
            if h_set not in hero_groups:
                hero_groups[h_set] = []
            hero_groups[h_set].append(i)
        if not hero_nodes:
            hero_groups = {frozenset(): list(range(len(node_sets)))}
            
        # 1. Run Complete Linkage
        comp_clusters = []
        for indices in hero_groups.values():
            group_pairs = [(node_sets[i], i) for i in indices]
            c = cluster_talents_hac(group_pairs, node_ranks_list, node_meta, threshold=0.3, pick_rates=analysis.pick_rates)
            comp_clusters.extend(c)
        comp_scores = calculate_silhouette_scores(comp_clusters, node_ranks_list, node_meta, pick_rates=analysis.pick_rates)
        comp_mean = round(sum(comp_scores.values()) / len(comp_scores), 3) if comp_scores else 0.0
        
        # 2. Run Average Linkage
        avg_clusters = []
        for indices in hero_groups.values():
            group_pairs = [(node_sets[i], i) for i in indices]
            c = cluster_talents_hac_average(group_pairs, node_ranks_list, node_meta, threshold=0.3, pick_rates=analysis.pick_rates)
            avg_clusters.extend(c)
        avg_scores = calculate_silhouette_scores(avg_clusters, node_ranks_list, node_meta, pick_rates=analysis.pick_rates)
        avg_mean = round(sum(avg_scores.values()) / len(avg_scores), 3) if avg_scores else 0.0
        
        rec = "Complete Linkage (current)" if comp_mean >= avg_mean else "Average Linkage"
        print(f"| `{spec}` | {len(comp_clusters)} / {comp_mean:.3f} | {len(avg_clusters)} / {avg_mean:.3f} | **{rec}** |")

if __name__ == "__main__":
    test_linkage_comparison()
