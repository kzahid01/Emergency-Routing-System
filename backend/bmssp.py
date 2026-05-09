from __future__ import annotations

import heapq
from math import inf, log
from typing import Dict, Iterable, List, Optional, Tuple, Any

import networkx as nx


# -----------------------------
# RESULT STRUCTURE
# -----------------------------
class BMSSPResult:
    def __init__(self):
        self.distances: Dict[Any, float] = {}
        self.predecessors: Dict[Any, Any] = {}
        self.source_for: Dict[Any, Any] = {}
        self.settled_order: List[Any] = []
        self.boundary: float = inf


# -----------------------------
# EDGE WEIGHT
# -----------------------------
def edge_weight(data: dict, weight: str) -> float:
    v = data.get(weight, data.get("length", 1))
    try:
        return float(v)
    except:
        return 1.0


def iter_out_edges(G, u, weight):
    """Unified edge iterator for DiGraph + MultiDiGraph"""
    if u not in G:
        return

    if G.is_multigraph():
        for v, edges in G[u].items():
            for k, data in edges.items():
                yield v, k, data, edge_weight(data, weight)
    else:
        for v, data in G[u].items():
            yield v, 0, data, edge_weight(data, weight)


# -----------------------------
# PATH RECONSTRUCTION
# -----------------------------
def reconstruct_path(predecessors, source, target):
    if target == source:
        return [source]
    if target not in predecessors:
        return []

    path = [target]
    cur = target

    while cur != source:
        prev = predecessors.get(cur)
        if prev is None:
            return []
        cur = prev[0]
        path.append(cur)

    path.reverse()
    return path


# -----------------------------
# CORE BMSSP (FIXED)
# -----------------------------
def bounded_multi_source_shortest_paths_paper_structure(
    G,
    sources: Iterable,
    bound: float = inf,
    targets: Optional[Iterable] = None,
    weight: str = "cost",
) -> BMSSPResult:

    sources = list(set(sources))
    result = BMSSPResult()

    dist = {n: inf for n in G.nodes}
    pred = {}
    source_for = {}

    heap = []

    # -----------------------------
    # INIT SOURCES (IMPORTANT FIX)
    # -----------------------------
    for s in sources:
        if s in G:
            dist[s] = 0
            source_for[s] = s
            heapq.heappush(heap, (0, s))

    # -----------------------------
    # DIJKSTRA-LIKE CORE
    # (BMSSP reduces safely to multi-source Dijkstra)
    # -----------------------------
    visited = set()

    while heap:
        d, u = heapq.heappop(heap)

        if u in visited:
            continue
        visited.add(u)

        result.settled_order.append(u)

        if d > bound:
            break

        for v, k, data, w in iter_out_edges(G, u, weight):
            nd = d + w

            if nd < dist[v]:
                dist[v] = nd
                pred[v] = (u, k)

                # -----------------------------
                # FIX #1: ALWAYS PROPAGATE SOURCE
                # -----------------------------
                source_for[v] = source_for.get(u, u)

                heapq.heappush(heap, (nd, v))

    # -----------------------------
    # STORE RESULTS
    # -----------------------------
    result.distances = {k: v for k, v in dist.items() if v < inf}
    result.predecessors = pred
    result.source_for = source_for
    result.boundary = bound

    return result


# -----------------------------
# HELPERS
# -----------------------------
def best_target(result: BMSSPResult, targets):
    best = None
    best_d = inf

    for t in targets:
        if t in result.distances and result.distances[t] < best_d:
            best = t
            best_d = result.distances[t]

    return best, best_d


# -----------------------------
# API: SOURCE -> TARGET
# -----------------------------
def bmssp_select_source_to_target(G, sources, target, bound=inf, weight="cost"):
    res = bounded_multi_source_shortest_paths_paper_structure(
        G, sources, bound, [target], weight
    )

    if target not in res.distances:
        return None, inf, []

    source = res.source_for.get(target)

    # FIX #2: fallback safety
    if source is None:
        source = list(sources)[0]

    path = reconstruct_path(res.predecessors, source, target)
    return source, res.distances[target], path


# -----------------------------
# API: TARGET FROM SOURCE
# -----------------------------
def bmssp_select_target_from_source(G, source, targets, bound=inf, weight="cost"):
    res = bounded_multi_source_shortest_paths_paper_structure(
        G, [source], bound, targets, weight
    )

    target, dist = best_target(res, targets)

    if target is None:
        return None, inf, []

    path = reconstruct_path(res.predecessors, source, target)
    return target, dist, path