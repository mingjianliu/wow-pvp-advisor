import json
import os
import sqlite3
from wow_advisor.processor.talents import summarize_talent_clusters
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore

def test_clustering(spec, bracket, threshold):
    conn = get_default_db()
    store = CacheStore(conn)
    players = store.get_players(spec, bracket)
    if not players:
        print(f"No players found for {spec} {bracket}")
        return
    
    players_with_talent = [p for p in players if p.talent]
    node_sets = [p.talent.all_node_ids for p in players_with_talent]
    node_ranks_list = [p.talent.node_ranks for p in players_with_talent]
    
    from wow_advisor.talent_tree import get_tree_structure
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

    from wow_advisor.processor.talents import cluster_talents
    
    hero_nodes = {nid for nid, meta in node_meta.items() if meta.get("is_hero")}
    hero_groups = {}
    for i, nodes in enumerate(node_sets):
        h_set = frozenset(nodes & hero_nodes)
        if h_set not in hero_groups: hero_groups[h_set] = []
        hero_groups[h_set].append(i)
    
    total_clusters = 0
    print(f"\n--- Threshold {threshold} ---")
    for h_set, indices in hero_groups.items():
        group_pairs = [(node_sets[i], i) for i in indices]
        group_clusters = cluster_talents(group_pairs, node_ranks_list, node_meta, threshold=threshold)
        total_clusters += len(group_clusters)
        print(f"Hero Set: {len(indices)} players -> {len(group_clusters)} clusters")
    
    print(f"Total clusters = {total_clusters}")

if __name__ == "__main__":
    test_clustering("restoration-shaman", "3v3", 10.0)
    test_clustering("restoration-shaman", "3v3", 20.0)
    test_clustering("restoration-shaman", "3v3", 30.0)
