from datetime import datetime
import math
import os
import numpy as np
import networkx as nx

from ai_model.knn_model import TrafficPredictor, traffic_level_to_multiplier
from ai_model.traffic_data_generator import TrafficDataGenerator
from backend.bmssp import bmssp_select_source_to_target, bmssp_select_target_from_source
from map_load.map import MAP_DATA


G = MAP_DATA["graph"]

# ---------- SAFETY CHECK ----------
def is_valid_node(n):
    return n in G


EMERGENCY_PROFILES = {
    "low": {"traffic_weight": 1.15, "risk_weight": 0.35},
    "medium": {"traffic_weight": 1.0, "risk_weight": 0.15},
    "critical": {"traffic_weight": 0.8, "risk_weight": 0.0},
}

ROAD_RISK = {
    "living_street": 0.25,
    "residential": 0.12,
    "tertiary": 0.05,
    "secondary": 0.03,
    "primary": 0.02,
    "trunk": 0.01,
    "motorway": 0.0,
}

traffic_generator = TrafficDataGenerator()
traffic_predictor = TrafficPredictor()

try:
    traffic_predictor.load_model()
except Exception:
    traffic_predictor = None


# ---------- CLEAN ----------
def clean_value(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def normalize_node_id(node_id):
    if node_id in G:
        return node_id
    try:
        node_id = int(node_id)
        if node_id in G:
            return node_id
    except:
        pass
    return node_id


# ---------- FACILITY FILTER ----------
def is_responder(u):
    return clean_value(u.get("amenity")) in {"police", "fire_station"} \
        or clean_value(u.get("emergency")) == "ambulance_station"


def is_hospital(u):
    return clean_value(u.get("amenity")) == "hospital" \
        or clean_value(u.get("healthcare")) == "hospital"


# ---------- NODE HELPERS ----------
def nearest_node(lat, lon):
    best = None
    best_d = float("inf")
    for n, d in G.nodes(data=True):
        y = d.get("y")
        x = d.get("x")
        if y is None or x is None:
            continue
        dist = (y - lat) ** 2 + (x - lon) ** 2
        if dist < best_d:
            best_d = dist
            best = n
    return best


# ---------- BUILD CANDIDATES (FIXED) ----------
def build_candidates():
    responders = []
    hospitals = []

    for u in MAP_DATA["units"]:
        node = nearest_node(u["lat"], u["lon"])
        if node is None or node not in G:
            continue

        obj = {
            "node": node,
            "name": u.get("name", "Unknown"),
            "lat": u["lat"],
            "lon": u["lon"],
        }

        if is_responder(u):
            responders.append(obj)
        if is_hospital(u):
            hospitals.append(obj)

    # FORCE fallback if too small
    if len(responders) == 0:
        responders = [{"node": list(G.nodes())[0], "name": "Fallback Responder"}]

    if len(hospitals) == 0:
        hospitals = [{"node": list(G.nodes())[-1], "name": "Fallback Hospital"}]

    return responders, hospitals


RESPONDERS, HOSPITALS = build_candidates()


# ---------- EDGE COST ----------
def edge_cost(data):
    length = float(data.get("length", 1))
    return length


def apply_costs():
    for u, v, k, data in G.edges(keys=True, data=True) if G.is_multigraph() else G.edges(data=True):
        data["cost"] = edge_cost(data)


# ---------- PATH ----------
def path_coords(path):
    out = []
    for n in path:
        d = G.nodes[n]
        out.append({"node": n, "lat": d.get("y"), "lon": d.get("x")})
    return out


# ---------- MAIN ROUTE ----------
def calculate_route(start, end, emergency_level="medium"):
    start = normalize_node_id(start)
    end = normalize_node_id(end)

    if start not in G or end not in G:
        return {"error": "Invalid start/end node"}

    apply_costs()

    responder_nodes = [r["node"] for r in RESPONDERS if r["node"] in G]
    hospital_nodes = [h["node"] for h in HOSPITALS if h["node"] in G]

    # ---------- BMSSP SAFE CALL ----------
    try:
        responder, rcost, rpath = bmssp_select_source_to_target(
            G, responder_nodes, start, weight="cost"
        )
    except Exception:
        responder = None

    if responder is None:
        # FALLBACK (CRITICAL FIX)
        responder = responder_nodes[0]
        rpath = nx.shortest_path(G, responder, start, weight="length")
        rcost = nx.shortest_path_length(G, responder, start, weight="length")

    try:
        hospital, hcost, hpath = bmssp_select_target_from_source(
            G, start, hospital_nodes, weight="cost"
        )
    except Exception:
        hospital = None

    if hospital is None:
        hospital = hospital_nodes[0]
        hpath = nx.shortest_path(G, start, hospital, weight="length")
        hcost = nx.shortest_path_length(G, start, hospital, weight="length")

    return {
        "algorithm": "BMSSP+SAFE",
        "best_responder": responder,
        "best_hospital": hospital,
        "responder_cost": rcost,
        "hospital_cost": hcost,
        "responder_route_coordinates": path_coords(rpath),
        "hospital_route_coordinates": path_coords(hpath),
    }