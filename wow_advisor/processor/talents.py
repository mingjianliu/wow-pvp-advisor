from collections import Counter
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
            dist = [round(counts.get(r, 0) / n * 100, 1) for r in range(1, max_r + 1)]
            rank_distributions[node] = dist

    return TalentAnalysis(
        core_nodes=core,
        flex_nodes=flex,
        contested_nodes=contested,
        pick_rates=pick_rates,
        rank_distributions=rank_distributions,
        node_meta=node_meta or {},
    )


def _weighted_distance(
    set_a: set[int],
    ranks_a: dict[int, int],
    set_b: set[int],
    ranks_b: dict[int, int],
    node_meta: dict[int, dict]
) -> float:
    all_nodes = set_a | set_b
    distance = 0.0

    for nid in all_nodes:
        meta = node_meta.get(nid, {"row": 0, "type": "circle"})
        row = meta.get("row", 0)
        is_choice = meta.get("type") == "diamond"

        # Base weight by row/type
        if is_choice:
            weight = 10.0
        elif row >= 5:  # Apex (8-10) and Key (5-7)
            weight = 5.0
        else:  # Utility (1-4)
            weight = 2.0

        in_a = nid in set_a
        in_b = nid in set_b

        if in_a != in_b:
            # One build has it, other doesn't
            distance += weight
        elif in_a and in_b:
            # Both have it, check rank difference
            rank_a = ranks_a.get(nid, 1)
            rank_b = ranks_b.get(nid, 1)
            if rank_a != rank_b:
                distance += abs(rank_a - rank_b) * 0.5

    return distance


def cluster_talents(
    pairs: list[tuple[set[int], int]],  # (node_set, original_index)
    node_ranks_list: list[dict[int, int]],
    node_meta: dict[int, dict],
    threshold: float = 5.0,
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
            if _weighted_distance(nodes_i, ranks_i, nodes_j, ranks_j, node_meta) <= threshold:
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
        group_clusters = cluster_talents(
            group_pairs,
            node_ranks_list=node_ranks_list or [{} for _ in range(n)],
            node_meta=node_meta or {},
            threshold=5.0,
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
        # We prefer an index where the decision set matches the modal one
        canonical_idx = next(
            (idx for nodes, idx in cluster if (nodes & decision_nodes) == canonical_decision_set),
            cluster[0][1],
        )
        canonical_code = (
            loadout_codes[canonical_idx] if canonical_idx < len(loadout_codes) else ""
        )

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
            takes_with_ranks.append({"id": nid, "rank": modal_rank})

        cluster_summaries.append(
            {
                "rank": rank,
                "count": len(cluster),
                "pct": round(len(cluster) / n * 100, 1),
                "canonical_code": canonical_code,
                "takes": takes_with_ranks,
                "skips": sorted(decision_nodes - canonical_decision_set),
            }
        )

    return {
        "core_nodes": sorted(analysis.core_nodes),
        "flex_nodes": sorted(analysis.flex_nodes),
        "contested_nodes": sorted(decision_nodes),
        "pick_rates": {
            node: round(rate * 100, 1) for node, rate in analysis.pick_rates.items()
        },
        "rank_distributions": {
            str(node): dist for node, dist in analysis.rank_distributions.items()
        },
        "clusters": cluster_summaries,
        "clustering_method": method,
    }
