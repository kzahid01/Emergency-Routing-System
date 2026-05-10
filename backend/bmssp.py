import heapq
from math import inf


def reconstruct_path(pred, source, target):

    if source == target:
        return [source]

    path = [target]
    current = target

    while current != source:

        if current not in pred:
            return []

        current = pred[current]
        path.append(current)

    return list(reversed(path))


def bmssp_select_source_to_target(
    G,
    sources,
    target,
    weight="cost"
):

    dist = {
        node: inf for node in G.nodes
    }

    pred = {}

    source_for = {}

    heap = []

    for source in sources:

        dist[source] = 0

        source_for[source] = source

        heapq.heappush(
            heap,
            (0, source)
        )

    visited = set()

    while heap:

        current_dist, u = heapq.heappop(heap)

        if u in visited:
            continue

        visited.add(u)

        if u == target:
            break

        for v in G.neighbors(u):

            edge_data = G[u][v]

            if G.is_multigraph():
                edge_data = list(
                    edge_data.values()
                )[0]

            weight_value = float(
                edge_data.get(weight, 1)
            )

            new_dist = (
                current_dist +
                weight_value
            )

            if new_dist < dist[v]:

                dist[v] = new_dist

                pred[v] = u

                source_for[v] = source_for[u]

                heapq.heappush(
                    heap,
                    (new_dist, v)
                )

    if dist[target] == inf:
        return None, inf, []

    source = source_for[target]

    path = reconstruct_path(
        pred,
        source,
        target
    )

    return (
        source,
        dist[target],
        path
    )


def bmssp_select_target_from_source(
    G,
    source,
    targets,
    weight="cost"
):

    dist = {
        node: inf for node in G.nodes
    }

    pred = {}

    heap = [(0, source)]

    dist[source] = 0

    visited = set()

    while heap:

        current_dist, u = heapq.heappop(heap)

        if u in visited:
            continue

        visited.add(u)

        for v in G.neighbors(u):

            edge_data = G[u][v]

            if G.is_multigraph():
                edge_data = list(
                    edge_data.values()
                )[0]

            weight_value = float(
                edge_data.get(weight, 1)
            )

            new_dist = (
                current_dist +
                weight_value
            )

            if new_dist < dist[v]:

                dist[v] = new_dist

                pred[v] = u

                heapq.heappush(
                    heap,
                    (new_dist, v)
                )

    best_target = None

    best_distance = inf

    for target in targets:

        if dist[target] < best_distance:

            best_distance = dist[target]

            best_target = target

    if best_target is None:
        return None, inf, []

    path = reconstruct_path(
        pred,
        source,
        best_target
    )

    return (
        best_target,
        best_distance,
        path
    )