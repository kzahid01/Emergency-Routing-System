from map_load.map import MAP_DATA
import networkx as nx

G = MAP_DATA["graph"]

print(list(G.nodes())[:20])

# Use REAL node IDs from your graph
responders = [
    53094953,
    61088894,
    75779946
]

hospitals = [
    75780935,
    75780946,
    75780956
]


# ---------------------------------
# FIND BEST RESPONDER
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

    if best_cost == float("inf"):
        best_cost = -1

    return best_responder, best_cost


# ---------------------------------
# FIND BEST HOSPITAL
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

    if best_cost == float("inf"):
        best_cost = -1

    return best_hospital, best_cost


# ---------------------------------
# MAIN BMSSP ROUTING
# ---------------------------------
def calculate_route(incident_node):

    # Add traffic-aware cost
    for u, v, data in G.edges(data=True):

        traffic = data.get("traffic", 1)
        distance = data.get("length", 1)

        data["cost"] = distance * traffic

    # Find best responder
    responder, responder_cost = find_best_responder(
        G,
        incident_node,
        responders
    )

    # Find best hospital
    hospital, hospital_cost = find_best_hospital(
        G,
        incident_node,
        hospitals
    )

    if responder is None:
        return {
            "error": "No responder found"
        }

    if hospital is None:
        return {
            "error": "No hospital found"
        }

    # Responder path
    responder_path = nx.shortest_path(
        G,
        responder,
        incident_node,
        weight="cost"
    )

    # Hospital path
    hospital_path = nx.shortest_path(
        G,
        incident_node,
        hospital,
        weight="cost"
    )

    return {
        "best_responder": responder,
        "best_hospital": hospital,
        "responder_path": responder_path,
        "hospital_path": hospital_path,
        "responder_cost": responder_cost,
        "hospital_cost": hospital_cost
    }