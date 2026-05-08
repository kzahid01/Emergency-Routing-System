import os
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon

# Configuration
ox.settings.use_cache = True
ox.settings.cache_folder = "./osm_cache"
ox.settings.timeout = 180

GRAPH_FILE = "graph_cache.graphml"
FEATURES_FILE = "features_cache.geojson"

# G-8,Islamabad co-ordinates
coords = [
    (73.06253033859412, 33.69629712695355),
    (73.0617310860136, 33.69283221269566),
    (73.04742867141482, 33.68534192063541),
    (73.03741698119572, 33.69836200940986),
    (73.05428541723717, 33.70721594269111),
    (73.06257240451936, 33.69633212537474),
]
coords.append(coords[0])

sector_poly = Polygon(coords)

# OSM facilities tags
tags = {
    "amenity": ["hospital", "clinic", "doctors", "police", "fire_station"],
    "emergency": ["ambulance_station", "defibrillator", "fire_hydrant"],
    "healthcare": ["hospital", "clinic", "doctor"]
}

# LOAD / BUILD Road Graph
if os.path.exists(GRAPH_FILE):
    print("Loading cached graph...")
    G = ox.load_graphml(GRAPH_FILE)
else:
    print("Downloading graph...")
    G = ox.graph_from_polygon(
        sector_poly,
        network_type="drive",
        simplify=True
    )
    ox.save_graphml(G, GRAPH_FILE)
    print("Graph saved.")

# LOAD / BUILD Facilities
if os.path.exists(FEATURES_FILE):
    print("Loading cached features...")
    amenities = gpd.read_file(FEATURES_FILE)
else:
    print("Downloading features...")
    amenities = ox.features_from_polygon(sector_poly, tags=tags)
    amenities.to_file(FEATURES_FILE, driver="GeoJSON")
    print("Features saved.")

# Clean Geometry
if amenities is None or amenities.empty:
    points = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
else:
    points = amenities.copy()
    points = points[points.geometry.notna()]
    points = points[points.is_valid]

    points["geometry"] = points["geometry"].apply(
        lambda g: g.centroid if g.geom_type != "Point" else g
    )

    points = points.set_crs("EPSG:4326", allow_override=True)


for col in ["name", "amenity", "emergency", "healthcare"]:
    if col not in points.columns:
        points[col] = None

# Split categories
units_mask = (
    points["amenity"].isin(["hospital", "clinic", "doctors", "police", "fire_station"])
    | points["emergency"].isin(["ambulance_station"])
    | points["healthcare"].isin(["hospital", "clinic", "doctor"])
)

infra_mask = points["emergency"].isin(["fire_hydrant", "defibrillator"])

units = points[units_mask].copy()
infra = points[infra_mask].copy()

# export helpers
def to_json(gdf):
    data = []

    for _, row in gdf.iterrows():
        if row.geometry is None:
            continue

        data.append({
            "name": row.get("name", "Unknown"),
            "amenity": row.get("amenity"),
            "emergency": row.get("emergency"),
            "healthcare": row.get("healthcare"),
            "lat": row.geometry.y,
            "lon": row.geometry.x
        })

    return data

units_json = to_json(units)
infra_json = to_json(infra)

# eport graph structure
nodes, edges = ox.graph_to_gdfs(G)

nodes_json = [
    {
        "id": int(idx),
        "lat": row.geometry.y,
        "lon": row.geometry.x
    }
    for idx, row in nodes.iterrows()
]

edges_json = []
for (u, v, k), row in edges.iterrows():
    if row.geometry is None:
        continue

    coords = list(row.geometry.coords)

    edges_json.append({
        "u": int(u),
        "v": int(v),
        "key": int(k),
        "length": float(row.get("length", 0)),
        "highway": str(row.get("highway")),
        "coordinates": [[lat, lon] for lon, lat in coords]
    })

# output summary
print("\n===== MAP BUILD COMPLETE =====")
print(f"Nodes: {len(nodes_json)}")
print(f"Edges: {len(edges_json)}")
print(f"Units: {len(units_json)}")
print(f"Infrastructure: {len(infra_json)}")

# EXPORTS FOR OTHER FILES
MAP_DATA = {
    "graph": G,
    "nodes": nodes_json,
    "edges": edges_json,
    "units": units_json,
    "infra": infra_json
}