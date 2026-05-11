from datetime import datetime
import networkx as nx

from backend.bmssp import (
    bmssp_select_source_to_target,
    bmssp_select_target_from_source,
)

from ai_model.knn_model import (
    TrafficPredictor,
    traffic_level_to_multiplier,
)

from map_load.map import MAP_DATA


# ----------------------------
# GRAPH LOAD
# ----------------------------
G = MAP_DATA["graph"]

# ----------------------------
# TRAFFIC MODEL
# ----------------------------
traffic_predictor = TrafficPredictor()

try:
    traffic_predictor.load_model()
except:
    traffic_predictor = None


# ----------------------------
# NEAREST NODE
# ----------------------------
def nearest_node(lat, lon):
    best_node = None
    best_distance = float("inf")

    for node, data in G.nodes(data=True):
        node_lat = data.get("y")
        node_lon = data.get("x")

        if node_lat is None or node_lon is None:
            continue

        distance = (node_lat - lat) ** 2 + (node_lon - lon) ** 2

        if distance < best_distance:
            best_distance = distance
            best_node = node

    return best_node


# ----------------------------
# PATH CONVERTER
# ----------------------------
def path_coordinates(path):
    result = []

    for node in path:
        data = G.nodes[node]

        result.append({
            "node": node,
            "lat": data.get("y"),
            "lon": data.get("x"),
        })

    return result


# ----------------------------
# TRAFFIC MULTIPLIER
# ----------------------------
def get_traffic_multiplier(edge_data):
    if not traffic_predictor:
        return 1.0

    try:
        hour = datetime.now().hour

        road_type = edge_data.get("highway", "residential")
        length = float(edge_data.get("length", 1))

        traffic_level = traffic_predictor.predict(
            hour=hour,
            road_type=str(road_type),
            length=length
        )

        return traffic_level_to_multiplier(traffic_level)

    except:
        return 1.0


# ----------------------------
# APPLY COSTS TO GRAPH
# ----------------------------
def apply_costs():
    if G.is_multigraph():
        for u, v, k, data in G.edges(keys=True, data=True):
            length = float(data.get("length", 1))
            multiplier = get_traffic_multiplier(data)
            data["cost"] = length * multiplier

    else:
        for u, v, data in G.edges(data=True):
            length = float(data.get("length", 1))
            multiplier = get_traffic_multiplier(data)
            data["cost"] = length * multiplier


# ----------------------------
# OPTIONAL ROUTE FUNCTION (FIXED)
# ----------------------------
def get_route(start_node, end_node):
    """
    Simple shortest path (fallback)
    """
    try:
        apply_costs()

        path = nx.shortest_path(
            G,
            start_node,
            end_node,
            weight="cost"
        )

        return {
            "path": path,
            "coordinates": path_coordinates(path)
        }

    except Exception as e:
        return {"error": str(e)}


# ----------------------------
# MAIN EMERGENCY FUNCTION
# ----------------------------
def calculate_emergency_dispatch(
    emergency_lat,
    emergency_lon,
    emergency_level="critical"
):

    emergency_node = nearest_node(
        emergency_lat,
        emergency_lon
    )

    if emergency_node not in G:
        return {"error": "Invalid location"}

    apply_costs()

    responders = []
    hospitals = []

    for node, data in G.nodes(data=True):
        amenity = data.get("amenity")

        if amenity in ["hospital", "police", "fire_station"]:
            responders.append(node)

        if amenity == "hospital":
            hospitals.append(node)

    if not responders:
        responders = [list(G.nodes())[0]]

    if not hospitals:
        hospitals = [list(G.nodes())[-1]]

    responder_node, responder_cost, responder_path = bmssp_select_source_to_target(
        G,
        responders,
        emergency_node,
        weight="cost"
    )

    hospital_node, hospital_cost, hospital_path = bmssp_select_target_from_source(
        G,
        emergency_node,
        hospitals,
        weight="cost"
    )

    return {
        "algorithm": "BMSSP_TRAFFIC_AI",
        "best_responder": responder_node,
        "best_hospital": hospital_node,
        "responder_cost": responder_cost,
        "hospital_cost": hospital_cost,
        "responder_route_coordinates": path_coordinates(responder_path),
        "hospital_route_coordinates": path_coordinates(hospital_path),
    }