from collections import Counter
from dataclasses import dataclass, field


@dataclass
class TalentAnalysis:
    core_nodes: set[int] = field(default_factory=set)
    flex_nodes: set[int] = field(default_factory=set)
    contested_nodes: set[int] = field(default_factory=set)
    pick_rates: dict[int, float] = field(default_factory=dict)


def analyze_talents(
    node_sets: list[set[int]],
    core_threshold: float = 0.8,
    flex_threshold: float = 0.2,
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
    return TalentAnalysis(
        core_nodes=core,
        flex_nodes=flex,
        contested_nodes=contested,
        pick_rates=pick_rates,
    )


def _hamming(a: set[int], b: set[int]) -> int:
    return len(a.symmetric_difference(b))


def cluster_talents(
    contested_pairs: list[tuple[set[int], int]],
    threshold: int = 2,
) -> list[list[tuple[set[int], int]]]:
    """Greedy Hamming clustering. Returns clusters sorted by size descending."""
    assigned = [False] * len(contested_pairs)
    clusters: list[list[tuple[set[int], int]]] = []
    for i, (nodes_i, idx_i) in enumerate(contested_pairs):
        if assigned[i]:
            continue
        cluster = [(nodes_i, idx_i)]
        assigned[i] = True
        for j in range(i + 1, len(contested_pairs)):
            if assigned[j]:
                continue
            if _hamming(nodes_i, contested_pairs[j][0]) <= threshold:
                cluster.append(contested_pairs[j])
                assigned[j] = True
        clusters.append(cluster)
    return sorted(clusters, key=len, reverse=True)


def summarize_talent_clusters(
    node_sets: list[set[int]],
    loadout_codes: list[str],
    keystone_nodes: list[int] | None = None,
) -> dict:
    """Full pipeline: analyze → cluster → summarize."""
    n = len(node_sets)
    if n == 0:
        return {"core_nodes": [], "flex_nodes": [], "contested_nodes": [],
                "clusters": [], "clustering_method": "variance+hamming"}

    analysis = analyze_talents(node_sets)

    if keystone_nodes is not None:
        decision_nodes = set(keystone_nodes)
        method = "keystone"
    else:
        decision_nodes = analysis.contested_nodes
        method = "variance+hamming"

    contested_pairs = [(node_sets[i] & decision_nodes, i) for i in range(n)]
    clusters = cluster_talents(contested_pairs, threshold=1)

    cluster_summaries = []
    for rank, cluster in enumerate(clusters, 1):
        counts = Counter(frozenset(nodes) for nodes, _ in cluster)
        canonical_set = set(counts.most_common(1)[0][0])
        canonical_idx = next(
            (idx for nodes, idx in cluster if set(nodes) == canonical_set),
            cluster[0][1],
        )
        canonical_code = loadout_codes[canonical_idx] if canonical_idx < len(loadout_codes) else ""
        cluster_summaries.append({
            "rank": rank,
            "count": len(cluster),
            "pct": round(len(cluster) / n * 100, 1),
            "canonical_code": canonical_code,
            "takes": sorted(canonical_set),
            "skips": sorted(decision_nodes - canonical_set),
        })

    return {
        "core_nodes": sorted(analysis.core_nodes),
        "flex_nodes": sorted(analysis.flex_nodes),
        "contested_nodes": sorted(decision_nodes),
        "pick_rates": {node: round(rate * 100, 1) for node, rate in analysis.pick_rates.items()},
        "clusters": cluster_summaries,
        "clustering_method": method,
    }
