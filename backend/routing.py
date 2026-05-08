from graph import create_graph
import networkx as nx

def calculate_route(start, end):

    G = create_graph()

    # BMSSP traffic-aware cost
    for u, v, data in G.edges(data=True):

        traffic = data.get("traffic", 1)
        distance = data["weight"]

        data["cost"] = distance * traffic

    path = nx.shortest_path(
        G,
        start,
        end,
        weight="cost"
    )

    distance = nx.shortest_path_length(
        G,
        start,
        end,
        weight="cost"
    )

    return path, distance