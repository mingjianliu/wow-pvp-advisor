from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class TalentAnalysis:
    core_nodes: set[int] = field(default_factory=set)
    flex_nodes: set[int] = field(default_factory=set)
    contested_nodes: set[int] = field(default_factory=set)
    pick_rates: dict[int, float] = field(default_factory=dict)
    rank_distributions: dict[int, list[float]] = field(default_factory=dict)
    node_meta: dict[int, dict] = field(default_factory=dict)


def analyze_talents(
    node_sets: list[set[int]],
    node_ranks_list: list[dict[int, int]] | None = None,
    core_threshold: float = 0.8,
    flex_threshold: float = 0.2,
    node_meta: dict[int, dict] | None = None,
) -> TalentAnalysis:
    if not node_sets:
        return TalentAnalysis()
    n = len(node_sets)
    all_nodes: set[int] = set().union(*node_sets)
    pick_counts: dict[int, int] = {node: 0 for node in all_nodes}
    for nodes in node_sets:
        for node in nodes:
            pick_counts[node] += 1
    pick_rates = {node: count / n for node, count in pick_counts.items()}
    core = {node for node, rate in pick_rates.items() if rate >= core_threshold}
    flex = {node for node, rate in pick_rates.items() if rate <= flex_threshold}
    contested = all_nodes - core - flex

    rank_distributions = {}
    if node_ranks_list:
        for node in all_nodes:
            # We track whatever ranks we see. Usually it's 1 or 2.
            ranks_seen = [ranks.get(node, 0) for ranks in node_ranks_list if node in ranks]
            if not ranks_seen:
                continue
            max_r = max(ranks_seen)
            counts = Counter(ranks_seen)
            # list index i corresponds to rank i+1
            # Denominator is pick_counts[node] to show distribution among those who took it
            pick_count = pick_counts[node]
            dist = [round(counts.get(r, 0) / pick_count * 100, 1) for r in range(1, max_r + 1)]
            rank_distributions[node] = dist

    return TalentAnalysis(
        core_nodes=core,
        flex_nodes=flex,
        contested_nodes=contested,
        pick_rates=pick_rates,
        rank_distributions=rank_distributions,
        node_meta=node_meta or {},
    )


def _weighted_jaccard_distance(
    set_a: set[int],
    ranks_a: dict[int, int],
    set_b: set[int],
    ranks_b: dict[int, int],
    node_meta: dict[int, dict]
) -> float:
    all_nodes = set_a | set_b
    weighted_intersection = 0.0
    weighted_union = 0.0

    for nid in all_nodes:
        meta = node_meta.get(nid, {"row": 0, "type": "circle"})
        # Weights: Choice=20, Major=5, Utility=0.1
        weight = 20.0 if meta.get("type") == "diamond" else (5.0 if meta.get("row") >= 5 else 0.1)

        in_a = nid in set_a
        in_b = nid in set_b

        if in_a and in_b:
            rank_diff = abs(ranks_a.get(nid, 1) - ranks_b.get(nid, 1))
            # Shared node weight reduced by rank shuffles (0.01 per rank diff)
            weighted_intersection += max(0, weight - (rank_diff * 0.01))
            weighted_union += weight
        else:
            weighted_union += weight

    return 1.0 - (weighted_intersection / weighted_union) if weighted_union > 0 else 0.0


def cluster_talents_hac(
    pairs: list[tuple[set[int], int]],
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = 0.3,
) -> list[list[tuple[set[int], int]]]:
    """
    Cluster talent builds using Agglomerative Hierarchical Clustering (HAC)
    with Complete Linkage and Weighted Jaccard Distance.
    """
    if not pairs:
        return []

    # Every point starts as its own cluster (a list containing one pair and its original index)
    # We store (pair, original_index) to look up node_ranks
    clusters = [[(pairs[i], i)] for i in range(len(pairs))]
    
    while len(clusters) > 1:
        best_dist = float('inf')
        best_pair = (None, None)
        
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Complete Linkage: max distance between all members of clusters
                max_d = 0.0
                for (p_a, idx_a) in clusters[i]:
                    for (p_b, idx_b) in clusters[j]:
                        d = _weighted_jaccard_distance(
                            p_a[0], node_ranks_list[idx_a],
                            p_b[0], node_ranks_list[idx_b],
                            node_meta
                        )
                        if d > max_d:
                            max_d = d
                            # Optimization: if max_d already exceeds current best_dist, 
                            # we can stop checking this cluster pair
                            if max_d >= best_dist:
                                break
                    if max_d >= best_dist:
                        break
                
                if max_d < best_dist:
                    best_dist = max_d
                    best_pair = (i, j)
        
        if best_dist > threshold:
            break
            
        i, j = best_pair
        clusters[i].extend(clusters[j])
        clusters.pop(j)
        
    # Unwrap (pair, index) back to just pair for the return value
    final_clusters = []
    for c in clusters:
        final_clusters.append([p for p, idx in c])
        
    return sorted(final_clusters, key=len, reverse=True)


def cluster_talents(
    pairs: list[tuple[set[int], int]],  # (node_set, original_index)
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = 0.2,
) -> list[list[tuple[set[int], int]]]:
    """Greedy weighted distance clustering. Returns clusters sorted by size descending."""
    assigned = [False] * len(pairs)
    clusters: list[list[tuple[set[int], int]]] = []
    for i, (nodes_i, idx_i) in enumerate(pairs):
        if assigned[i]:
            continue
        cluster = [(nodes_i, idx_i)]
        assigned[i] = True
        ranks_i = node_ranks_list[idx_i]
        for j in range(i + 1, len(pairs)):
            if assigned[j]:
                continue
            nodes_j, idx_j = pairs[j]
            ranks_j = node_ranks_list[idx_j]
            if _weighted_jaccard_distance(nodes_i, ranks_i, nodes_j, ranks_j, node_meta) <= threshold:
                cluster.append(pairs[j])
                assigned[j] = True
        clusters.append(cluster)
    return sorted(clusters, key=len, reverse=True)


def summarize_talent_clusters(
    node_sets: list[set[int]],
    loadout_codes: list[str],
    keystone_nodes: list[int] | None = None,
    node_ranks_list: list[dict[int, int]] | None = None,
    node_meta: dict[int, dict] | None = None,
    player_info: list[dict] | None = None,
) -> dict:
    """Full pipeline: analyze → partition by hero → cluster → summarize."""
    n = len(node_sets)
    if n == 0:
        return {
            "core_nodes": [],
            "flex_nodes": [],
            "contested_nodes": [],
            "clusters": [],
            "clustering_method": "none",
        }

    analysis = analyze_talents(
        node_sets, node_ranks_list=node_ranks_list, node_meta=node_meta
    )
    
    global_pickers = defaultdict(list)
    if player_info:
        for i, nodes in enumerate(node_sets):
            p = player_info[i]
            p_obj = {"n": p["name"], "r": p["realm"]}
            for nid in nodes:
                global_pickers[nid].append(p_obj)

    if keystone_nodes is not None:
        decision_nodes = set(keystone_nodes)
        method = "keystone"
    else:
        decision_nodes = analysis.contested_nodes
        method = "variance+weighted"
        # Auto-limit to the 8 most contested nodes (closest to 50% pick rate).
        # With small samples, 10+ contested nodes fragment into dozens of 1-player clusters.
        MAX_DECISION = 8
        if len(decision_nodes) > MAX_DECISION:
            decision_nodes = set(
                sorted(
                    decision_nodes,
                    key=lambda nd: abs(0.5 - analysis.pick_rates.get(nd, 0)),
                )[:MAX_DECISION]
            )

    # Partition by Hero Tree choice
    hero_nodes = {
        nid for nid, meta in (node_meta or {}).items() if meta.get("is_hero")
    }
    hero_groups: dict[frozenset[int], list[int]] = {}
    for i in range(n):
        h_set = frozenset(node_sets[i] & hero_nodes)
        if h_set not in hero_groups:
            hero_groups[h_set] = []
        hero_groups[h_set].append(i)

    # If no hero nodes found (e.g. low level), treat as one group
    if not hero_nodes:
        hero_groups = {frozenset(): list(range(n))}

    all_clusters = []
    for indices in hero_groups.values():
        group_pairs = [(node_sets[i], i) for i in indices]
        group_clusters = cluster_talents_hac(
            group_pairs,
            node_ranks_list=node_ranks_list or [{} for _ in range(n)],
            node_meta=node_meta or {},
            threshold=0.3,
        )
        all_clusters.extend(group_clusters)

    # Sort combined clusters by size
    clusters = sorted(all_clusters, key=len, reverse=True)

    cluster_summaries = []
    for rank, cluster in enumerate(clusters, 1):
        # We find the most common set of decision nodes within this cluster
        counts = Counter(frozenset(nodes & decision_nodes) for nodes, _ in cluster)
        canonical_decision_set = set(counts.most_common(1)[0][0])

        # We also want the hero tree set for this cluster (should be uniform since we partitioned)
        hero_counts = Counter(frozenset(nodes & hero_nodes) for nodes, _ in cluster)
        canonical_hero_set = set(hero_counts.most_common(1)[0][0])

        # Pick a canonical index for the loadout code
        canonical_idx = next(
            (idx for nodes, idx in cluster if (nodes & decision_nodes) == canonical_decision_set),
            cluster[0][1],
        )
        canonical_code = (
            loadout_codes[canonical_idx] if canonical_idx < len(loadout_codes) else ""
        )

        cluster_pickers = defaultdict(list)
        if player_info:
            for nodes, idx in cluster:
                p = player_info[idx]
                p_obj = {"n": p["name"], "r": p["realm"]}
                for nid in nodes:
                    cluster_pickers[nid].append(p_obj)

        # Determine modal rank for each node in this cluster
        takes_with_ranks = []
        output_nodes = sorted(canonical_decision_set | canonical_hero_set)
        for nid in output_nodes:
            node_ranks_in_cluster = [
                node_ranks_list[idx].get(nid, 1)
                for _, idx in cluster
                if node_ranks_list and nid in node_ranks_list[idx]
            ]
            modal_rank = (
                Counter(node_ranks_in_cluster).most_common(1)[0][0]
                if node_ranks_in_cluster
                else 1
            )
            takes_with_ranks.append({
                "id": nid, 
                "rank": modal_rank,
                "pickers": cluster_pickers[nid]
            })

        # NEW: Find "Internal Flex" nodes (taken by some but not all members of the cluster)
        # This helps show variance within a broadly merged cluster.
        internal_counts = Counter()
        for nodes, _ in cluster:
            internal_counts.update(nodes)
        
        cluster_flex = []
        cluster_size = len(cluster)
        for nid, count in internal_counts.items():
            if nid in output_nodes:
                continue # Already in takes
            if nid in analysis.core_nodes:
                continue # Already global core
            pct = round(count / cluster_size * 100, 1)
            if pct >= 10.0: # Show if at least 10% take it
                cluster_flex.append({
                    "id": nid, 
                    "pct": pct,
                    "pickers": cluster_pickers[nid]
                })

        cluster_summaries.append(
            {
                "rank": rank,
                "count": len(cluster),
                "pct": round(len(cluster) / n * 100, 1),
                "canonical_code": canonical_code,
                "takes": takes_with_ranks,
                "flex_takes": sorted(cluster_flex, key=lambda x: x["pct"], reverse=True),
                "skips": [
                    {"id": nid, "pickers": cluster_pickers[nid]}
                    for nid in sorted(decision_nodes - canonical_decision_set - hero_nodes)
                ],
            }
        )

    return {
        "core_nodes": [{"id": nid, "pickers": global_pickers[nid]} for nid in sorted(analysis.core_nodes)],
        "flex_nodes": [{"id": nid, "pickers": global_pickers[nid]} for nid in sorted(analysis.flex_nodes)],
        "contested_nodes": [{"id": nid, "pickers": global_pickers[nid]} for nid in sorted(decision_nodes)],
        "pick_rates": {
            node: round(rate * 100, 1) for node, rate in analysis.pick_rates.items()
        },
        "rank_distributions": {
            str(node): dist for node, dist in analysis.rank_distributions.items()
        },
        "clusters": cluster_summaries,
        "clustering_method": method,
    }
