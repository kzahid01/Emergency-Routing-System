import networkx as nx

def create_graph():

    G = nx.Graph()

    # format: (node1, node2, distance, traffic)
    G.add_edge("G-8 Markaz", "F-8", weight=2, traffic=1)
    G.add_edge("F-8", "PIMS Hospital", weight=3, traffic=2)
    G.add_edge("G-8 Markaz", "F-7", weight=1, traffic=3)
    G.add_edge("F-7", "PIMS Hospital", weight=4, traffic=1)

    return G