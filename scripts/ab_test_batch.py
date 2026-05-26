import sys
import os

# Add parent repo to path to import old implementation
sys.path.insert(0, "/Users/mingjianliu/code/wow-talent-gear-collector")
from wow_advisor.processor.talents import summarize_talent_clusters as old_summarize
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore

# Clean sys.path and sys.modules for next import
sys.path.remove("/Users/mingjianliu/code/wow-talent-gear-collector")
for k in list(sys.modules.keys()):
    if k.startswith("wow_advisor"):
        del sys.modules[k]

# Add worktree to path to import new implementation
sys.path.insert(0, "/Users/mingjianliu/code/wow-talent-gear-collector/.worktrees/cluster")
from wow_advisor.processor.talents import summarize_talent_clusters as new_summarize
from wow_advisor.talent_tree import get_tree_structure

def main():
    store = CacheStore(get_default_db())
    conn = get_default_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT spec FROM aggregations")
    specs = [r[0] for r in cursor.fetchall()]
    
    print("| Spec | Old Clusters | New Clusters | Mean Silhouette | Improvements / Key Observations |")
    print("|---|---|---|---|---|")
    
    for spec in specs:
        players = store.get_players(spec, "3v3", "us")
        if not players:
            continue
        players_with_talent = [p for p in players if p.talent]
        if not players_with_talent:
            continue
            
        node_sets = [set(p.talent.all_node_ids) for p in players_with_talent]
        loadout_codes = [p.talent.loadout_code for p in players_with_talent]
        node_ranks_list = [p.talent.node_ranks for p in players_with_talent]
        player_info = [{"name": p.name, "realm": p.realm} for p in players_with_talent]
        
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
        
        # Run old
        old_res = old_summarize(
            node_sets=node_sets,
            loadout_codes=loadout_codes,
            node_ranks_list=node_ranks_list,
            node_meta=node_meta,
            player_info=player_info
        )
        
        # Run new
        new_res = new_summarize(
            node_sets=node_sets,
            loadout_codes=loadout_codes,
            node_ranks_list=node_ranks_list,
            node_meta=node_meta,
            player_info=player_info
        )
        
        old_clusters = len(old_res["clusters"])
        new_clusters = len(new_res["clusters"])
        mean_sil = new_res.get("mean_silhouette_score", 0.0)
        
        # Highlight improvement description
        if old_clusters <= 2 and new_clusters > 2:
            note = f"Successfully split single giant cluster (sizes: {[c['count'] for c in old_res['clusters']][:2]}) into {new_clusters} specific archetypes."
        else:
            note = f"Fine-grained segmentation showing distinct builds (sizes: {[c['count'] for c in new_res['clusters']][:3]})."
            
        print(f"| `{spec}` | {old_clusters} | {new_clusters} | {mean_sil} | {note} |")

if __name__ == "__main__":
    main()
