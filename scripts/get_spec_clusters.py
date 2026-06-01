#!/usr/bin/env python
import argparse
import json
import os
import sqlite3
import sys

def main():
    parser = argparse.ArgumentParser(description="Find best matching talent cluster for a spec.")
    parser.add_argument("--spec", required=True, help="Spec name (e.g. 'restoration shaman')")
    parser.add_argument("--talents", required=True, help="JSON-encoded dictionary of talent node ranks")
    parser.add_argument("--bracket", default="3v3", help="Bracket (default: '3v3')")
    parser.add_argument("--region", default="us", help="Region (default: 'us')")
    parser.add_argument("--locale", default="en_US", help="Locale (default: 'en_US')")
    parser.add_argument("--db", default=None, help="Path to wow_advisor.db database")
    args = parser.parse_args()

    # Determine database path
    if args.db:
        db_path = args.db
    else:
        # Default to data/wow_advisor.db relative to repo root
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "wow_advisor.db"))

    if not os.path.exists(db_path):
        print(json.dumps({"error": f"Database file not found at: {db_path}"}))
        sys.exit(1)

    # Normalize spec name
    normalized_spec = args.spec.lower().strip().replace(" ", "-")

    # Connect to the database
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(json.dumps({"error": f"Failed to connect to database: {e}"}))
        sys.exit(1)

    cursor = conn.cursor()

    # Fetch active talent clusters from aggregations
    cursor.execute(
        "SELECT data, region, locale FROM aggregations WHERE spec = ? AND bracket = ?",
        (normalized_spec, args.bracket)
    )
    rows = cursor.fetchall()

    if not rows:
        print(json.dumps({"error": f"No aggregations found for spec '{args.spec}' and bracket '{args.bracket}'"}))
        sys.exit(1)

    # Pick the best matching row based on region/locale
    selected_row = None
    for r in rows:
        if r["region"] == args.region and r["locale"] == args.locale:
            selected_row = r
            break
    if not selected_row:
        # Fallback to the first available row
        selected_row = rows[0]

    try:
        agg_data = json.loads(selected_row["data"])
    except Exception as e:
        print(json.dumps({"error": f"Failed to parse aggregations data JSON: {e}"}))
        sys.exit(1)

    clusters = agg_data.get("talents", {}).get("clusters", [])
    if not clusters:
        print(json.dumps({"error": f"No talent clusters found in aggregations data for spec '{args.spec}'"}))
        sys.exit(1)

    # Parse player's talents
    try:
        player_talents = json.loads(args.talents)
    except Exception as e:
        print(json.dumps({"error": f"Invalid JSON for talents: {e}"}))
        sys.exit(1)

    # Convert player talent keys to integers for set operations
    player_node_ids = {int(k) for k in player_talents.keys()}

    best_cluster = None
    min_dist = float("inf")

    # Compute Jaccard distance for each cluster and find the best match
    for cluster in clusters:
        cluster_node_ids = {int(item["id"]) for item in cluster.get("takes", [])}
        intersection = len(player_node_ids & cluster_node_ids)
        union = len(player_node_ids | cluster_node_ids)
        dist = 1.0 - (intersection / union) if union > 0 else 1.0

        # Minimize distance, tie break with higher pct, then lower rank
        if dist < min_dist:
            min_dist = dist
            best_cluster = cluster
        elif dist == min_dist:
            if best_cluster is not None:
                current_pct = cluster.get("pct", 0)
                best_pct = best_cluster.get("pct", 0)
                if current_pct > best_pct:
                    best_cluster = cluster
                elif current_pct == best_pct:
                    if cluster.get("rank", float("inf")) < best_cluster.get("rank", float("inf")):
                        best_cluster = cluster

    if not best_cluster:
        print(json.dumps({"error": "Failed to match player talents to any cluster"}))
        sys.exit(1)

    # Load talent node names from talent_node_cache
    cursor.execute(
        "SELECT nodes_json FROM talent_node_cache WHERE spec = ? AND locale = ?",
        (normalized_spec, args.locale)
    )
    cache_row = cursor.fetchone()
    if not cache_row:
        # Fallback to any locale for this spec
        cursor.execute(
            "SELECT nodes_json FROM talent_node_cache WHERE spec = ?",
            (normalized_spec,)
        )
        cache_row = cursor.fetchone()

    nodes_dict = {}
    if cache_row:
        try:
            nodes_dict = json.loads(cache_row["nodes_json"])
        except Exception:
            pass

    # Resolve node IDs to names for the player's talents
    nodes_info = {}
    for node_id_str in player_talents.keys():
        node_info = nodes_dict.get(str(node_id_str))
        if node_info and isinstance(node_info, dict):
            nodes_info[str(node_id_str)] = node_info.get("name")
        else:
            nodes_info[str(node_id_str)] = None

    # Prepare output result
    result = {
        "matched_cluster_rank": best_cluster.get("rank"),
        "matched_cluster_pct": best_cluster.get("pct"),
        "jaccard_distance": min_dist,
        "nodes_info": nodes_info
    }

    # Print results as a JSON string to stdout
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
