from collections import Counter, defaultdict
from dataclasses import dataclass, field

from wow_advisor.settings import (
    CORE_PICK_RATE,
    FLEX_PICK_RATE,
    HAC_THRESHOLD,
    MAX_DECISION_NODES,
    WEIGHT_CHOICE_NODE,
    WEIGHT_MAJOR_NODE,
    WEIGHT_UTILITY_NODE,
)


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
    core_threshold: float = CORE_PICK_RATE,
    flex_threshold: float = FLEX_PICK_RATE,
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
    node_meta: dict[int, dict],
    pick_rates: dict[int, float] | None = None,
) -> float:
    all_nodes = set_a | set_b
    weighted_intersection = 0.0
    weighted_union = 0.0

    for nid in all_nodes:
        meta = node_meta.get(nid, {"row": 0, "type": "circle"})
        if meta.get("type") == "diamond":
            weight = WEIGHT_CHOICE_NODE
        elif meta.get("row") >= 5:
            weight = WEIGHT_MAJOR_NODE
        else:
            weight = WEIGHT_UTILITY_NODE

        # Scale by pick rate variance/entropy if pick_rates is provided
        if pick_rates is not None:
            p = pick_rates.get(nid, 0.0)
            # Factor is 4 * p * (1 - p), ranging from 0.0 to 1.0
            scale = 4.0 * p * (1.0 - p)
            weight *= max(0.01, scale)

        in_a = nid in set_a
        in_b = nid in set_b

        if in_a and in_b:
            rank_diff = abs(ranks_a.get(nid, 1) - ranks_b.get(nid, 1))
            # Shared node weight reduced by rank shuffles (0.01 per rank diff)
            weighted_intersection += max(0.0, weight - (rank_diff * 0.01))
            weighted_union += weight
        else:
            weighted_union += weight

    return 1.0 - (weighted_intersection / weighted_union) if weighted_union > 0.0 else 0.0


def _calculate_medoid(
    cluster: list[tuple[set[int], int]],
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    pick_rates: dict[int, float] | None = None,
) -> tuple[set[int], int]:
    """
    Find the cluster member (node_set, original_index) that has the minimum
    sum of weighted Jaccard distances to all other members in the cluster.
    """
    if not cluster:
        raise ValueError("Cannot calculate medoid of an empty cluster")
    if len(cluster) == 1:
        return cluster[0]

    best_member = cluster[0]
    min_sum_dist = float('inf')

    for member_a, idx_a in cluster:
        sum_dist = 0.0
        for member_b, idx_b in cluster:
            if idx_a == idx_b:
                continue
            sum_dist += _weighted_jaccard_distance(
                member_a, node_ranks_list[idx_a],
                member_b, node_ranks_list[idx_b],
                node_meta,
                pick_rates=pick_rates,
            )
        if sum_dist < min_sum_dist:
            min_sum_dist = sum_dist
            best_member = (member_a, idx_a)

    return best_member


def cluster_talents_hac(
    pairs: list[tuple[set[int], int]],
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = HAC_THRESHOLD,
    pick_rates: dict[int, float] | None = None,
    linkage: str = "complete",
) -> list[list[tuple[set[int], int]]]:
    """
    Cluster talent builds using Agglomerative Hierarchical Clustering (HAC)
    with Weighted Jaccard Distance.

    linkage: "complete" (max pairwise distance) or "average" (mean pairwise distance).
    """
    if linkage not in ("complete", "average"):
        raise ValueError(f"Unknown linkage: {linkage!r}")
    if not pairs:
        return []

    # Every point starts as its own cluster (a list containing one pair and its
    # original index, so node_ranks can be looked up later)
    clusters = [[(pairs[i], i)] for i in range(len(pairs))]

    while len(clusters) > 1:
        best_dist = float('inf')
        best_pair = (None, None)

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                dists = [
                    _weighted_jaccard_distance(
                        p_a[0], node_ranks_list[idx_a],
                        p_b[0], node_ranks_list[idx_b],
                        node_meta,
                        pick_rates=pick_rates,
                    )
                    for (p_a, idx_a) in clusters[i]
                    for (p_b, idx_b) in clusters[j]
                ]
                d = max(dists) if linkage == "complete" else sum(dists) / len(dists)
                if d < best_dist:
                    best_dist = d
                    best_pair = (i, j)

        if best_dist > threshold:
            break

        i, j = best_pair
        clusters[i].extend(clusters[j])
        clusters.pop(j)

    # Unwrap (pair, index) back to just pair for the return value
    final_clusters = [[p for p, idx in c] for c in clusters]
    return sorted(final_clusters, key=len, reverse=True)


def cluster_talents_hac_average(
    pairs: list[tuple[set[int], int]],
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = HAC_THRESHOLD,
    pick_rates: dict[int, float] | None = None,
) -> list[list[tuple[set[int], int]]]:
    """HAC with Average Linkage — thin wrapper around cluster_talents_hac."""
    return cluster_talents_hac(
        pairs, node_ranks_list, node_meta,
        threshold=threshold, pick_rates=pick_rates, linkage="average",
    )


def cluster_talents(
    pairs: list[tuple[set[int], int]],  # (node_set, original_index)
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = 0.2,
    pick_rates: dict[int, float] | None = None,
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
            if _weighted_jaccard_distance(nodes_i, ranks_i, nodes_j, ranks_j, node_meta, pick_rates=pick_rates) <= threshold:
                cluster.append(pairs[j])
                assigned[j] = True
        clusters.append(cluster)
    return sorted(clusters, key=len, reverse=True)


def calculate_silhouette_scores(
    clusters: list[list[tuple[set[int], int]]],
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    pick_rates: dict[int, float] | None = None,
) -> dict[int, float]:
    """
    Calculate the silhouette score for each player index in the dataset.
    Returns a dictionary mapping original player index to their silhouette score.
    """
    scores = {}
    
    # Flatten clusters to map each index to its cluster id
    idx_to_cluster = {}
    for cluster_id, cluster in enumerate(clusters):
        for _, idx in cluster:
            idx_to_cluster[idx] = cluster_id

    # If there is only one cluster overall, all silhouette scores are 0.0
    if len(clusters) <= 1:
        return {idx: 0.0 for cluster in clusters for _, idx in cluster}

    # Precompute pairwise distances between all points in the dataset
    all_members = [item for cluster in clusters for item in cluster]
    n_points = len(all_members)
    dist_matrix = {}
    
    for i in range(n_points):
        nodes_a, idx_a = all_members[i]
        for j in range(i, n_points):
            nodes_b, idx_b = all_members[j]
            if idx_a == idx_b:
                dist = 0.0
            else:
                dist = _weighted_jaccard_distance(
                    nodes_a, node_ranks_list[idx_a],
                    nodes_b, node_ranks_list[idx_b],
                    node_meta,
                    pick_rates=pick_rates,
                )
            dist_matrix[(idx_a, idx_b)] = dist
            dist_matrix[(idx_b, idx_a)] = dist

    for nodes_a, idx_a in all_members:
        c_a = idx_to_cluster[idx_a]
        cluster_a = clusters[c_a]

        # 1. Calculate a(idx_a) - average distance to other members of same cluster
        if len(cluster_a) <= 1:
            a_val = 0.0
        else:
            same_cluster_dists = [dist_matrix[(idx_a, idx_b)] for _, idx_b in cluster_a if idx_b != idx_a]
            a_val = sum(same_cluster_dists) / len(same_cluster_dists)

        # 2. Calculate b(idx_a) - average distance to members of nearest other cluster
        min_other_cluster_dist = float('inf')
        for c_id, cluster_b in enumerate(clusters):
            if c_id == c_a:
                continue
            other_cluster_dists = [dist_matrix[(idx_a, idx_b)] for _, idx_b in cluster_b]
            avg_dist_to_b = sum(other_cluster_dists) / len(other_cluster_dists)
            if avg_dist_to_b < min_other_cluster_dist:
                min_other_cluster_dist = avg_dist_to_b

        b_val = min_other_cluster_dist if min_other_cluster_dist != float('inf') else 0.0

        # 3. Calculate s(idx_a)
        max_val = max(a_val, b_val)
        if max_val == 0.0:
            s_val = 0.0
        else:
            s_val = (b_val - a_val) / max_val
        scores[idx_a] = s_val

    return scores


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
        # Auto-limit to the most contested nodes (closest to 50% pick rate).
        # With small samples, 10+ contested nodes fragment into dozens of 1-player clusters.
        if len(decision_nodes) > MAX_DECISION_NODES:
            decision_nodes = set(
                sorted(
                    decision_nodes,
                    key=lambda nd: abs(0.5 - analysis.pick_rates.get(nd, 0)),
                )[:MAX_DECISION_NODES]
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

    # 1. Run Complete Linkage
    comp_clusters = []
    for indices in hero_groups.values():
        group_pairs = [(node_sets[i], i) for i in indices]
        group_clusters = cluster_talents_hac(
            group_pairs,
            node_ranks_list=node_ranks_list or [{} for _ in range(n)],
            node_meta=node_meta or {},
            threshold=HAC_THRESHOLD,
            pick_rates=analysis.pick_rates,
        )
        comp_clusters.extend(group_clusters)

    comp_scores = calculate_silhouette_scores(
        comp_clusters,
        node_ranks_list=node_ranks_list or [{} for _ in range(n)],
        node_meta=node_meta or {},
        pick_rates=analysis.pick_rates,
    )
    comp_mean = sum(comp_scores.values()) / len(comp_scores) if comp_scores else 0.0

    # 2. Run Average Linkage
    avg_clusters = []
    for indices in hero_groups.values():
        group_pairs = [(node_sets[i], i) for i in indices]
        group_clusters = cluster_talents_hac_average(
            group_pairs,
            node_ranks_list=node_ranks_list or [{} for _ in range(n)],
            node_meta=node_meta or {},
            threshold=HAC_THRESHOLD,
            pick_rates=analysis.pick_rates,
        )
        avg_clusters.extend(group_clusters)

    avg_scores = calculate_silhouette_scores(
        avg_clusters,
        node_ranks_list=node_ranks_list or [{} for _ in range(n)],
        node_meta=node_meta or {},
        pick_rates=analysis.pick_rates,
    )
    avg_mean = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0.0

    # Select the superior linkage based on silhouette score
    if comp_mean >= avg_mean:
        clusters = comp_clusters
        silhouette_scores = comp_scores
        linkage_type = "complete"
    else:
        clusters = avg_clusters
        silhouette_scores = avg_scores
        linkage_type = "average"

    # Sort combined clusters by size
    clusters = sorted(clusters, key=len, reverse=True)

    cluster_summaries = []
    for rank, cluster in enumerate(clusters, 1):
        # Find the medoid of the cluster
        medoid_nodes, medoid_idx = _calculate_medoid(
            cluster,
            node_ranks_list=node_ranks_list or [{} for _ in range(n)],
            node_meta=node_meta or {},
            pick_rates=analysis.pick_rates,
        )
        canonical_decision_set = medoid_nodes & decision_nodes
        canonical_hero_set = medoid_nodes & hero_nodes
        canonical_code = (
            loadout_codes[medoid_idx] if medoid_idx < len(loadout_codes) else ""
        )

        cluster_pickers = defaultdict(list)
        if player_info:
            for nodes, idx in cluster:
                p = player_info[idx]
                p_obj = {"n": p["name"], "r": p["realm"]}
                for nid in nodes:
                    cluster_pickers[nid].append(p_obj)

        # Determine rank for each node from the medoid player
        takes_with_ranks = []
        output_nodes = sorted(canonical_decision_set | canonical_hero_set)
        ranks_source = node_ranks_list or [{} for _ in range(n)]
        for nid in output_nodes:
            medoid_rank = ranks_source[medoid_idx].get(nid, 1)
            # Real share of this cluster's members that take the talent, so the
            # ratio (pickers/count) and the bar agree. Falls back to 100% only
            # when no picker roster is available (player_info omitted).
            take_pct = (
                round(len(cluster_pickers[nid]) / len(cluster) * 100, 1)
                if player_info else 100.0
            )
            takes_with_ranks.append({
                "id": nid,
                "rank": medoid_rank,
                "pct": take_pct,
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

        cluster_sil_scores = [silhouette_scores[idx] for _, idx in cluster]
        avg_sil = round(sum(cluster_sil_scores) / len(cluster_sil_scores), 3) if cluster_sil_scores else 0.0

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
                "silhouette_score": avg_sil,
                "pickers": (
                    [
                        {"n": player_info[idx]["name"], "r": player_info[idx]["realm"]}
                        for _, idx in cluster
                    ]
                    if player_info else []
                ),
            }
        )

    global_sil = round(sum(silhouette_scores.values()) / len(silhouette_scores), 3) if silhouette_scores else 0.0

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
        "linkage": linkage_type,
        "mean_silhouette_score": global_sil,
    }
