import networkx as nx

def shortest_path(G, source, target):
    return nx.shortest_path(G, source, target, weight="length")