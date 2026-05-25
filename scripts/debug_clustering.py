import json
import os

def test_clustering(spec, bracket, threshold):
    cache_path = os.path.expanduser(f"~/.gemini/tmp/wow-talent-gear-collector/cache/{spec}_{bracket}_us.json")
    if not os.path.exists(cache_path):
        print(f"No cache for {spec} {bracket}")
        return
    
    with open(cache_path) as f:
        players_data = json.load(f)
    
    node_sets = [set(p["talent"]["all_node_ids"]) for p in players_data if p.get("talent")]
    [p["talent"]["loadout_code"] for p in players_data if p.get("talent")]
    node_ranks_list = [p["talent"]["node_ranks"] for p in players_data if p.get("talent")]
    
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
    
    # Simulate partitioning
    hero_nodes = {nid for nid, meta in node_meta.items() if meta.get("is_hero")}
    hero_groups = {}
    for i, nodes in enumerate(node_sets):
        h_set = frozenset(nodes & hero_nodes)
        if h_set not in hero_groups:
            hero_groups[h_set] = []
        hero_groups[h_set].append(i)
    
    total_clusters = 0
    for h_set, indices in hero_groups.items():
        group_pairs = [(node_sets[i], i) for i in indices]
        group_clusters = cluster_talents(group_pairs, node_ranks_list, node_meta, threshold=threshold)
        total_clusters += len(group_clusters)
        print(f"Hero Set {list(h_set)[:3]}...: {len(indices)} players -> {len(group_clusters)} clusters")
    
    print(f"Threshold {threshold}: Total clusters = {total_clusters}")

if __name__ == "__main__":
    test_clustering("restoration-shaman", "3v3", 10.0)
    test_clustering("restoration-shaman", "3v3", 15.0)
    test_clustering("restoration-shaman", "3v3", 20.0)
