import networkx as nx


# ---------------------------------
# Find Best Responder
# ---------------------------------
def find_best_responder(G, incident_node, responders):

    best_responder = None
    best_cost = float("inf")

    for responder in responders:

        try:
            cost = nx.shortest_path_length(
                G,
                responder,
                incident_node,
                weight="cost"
            )

            if cost < best_cost:
                best_cost = cost
                best_responder = responder

        except:
            continue

    return best_responder, best_cost


# ---------------------------------
# Find Best Hospital
# ---------------------------------
def find_best_hospital(G, incident_node, hospitals):

    best_hospital = None
    best_cost = float("inf")

    for hospital in hospitals:

        try:
            cost = nx.shortest_path_length(
                G,
                incident_node,
                hospital,
                weight="cost"
            )

            if cost < best_cost:
                best_cost = cost
                best_hospital = hospital

        except:
            continue

    return best_hospital, best_cost