from fastapi import FastAPI
from pydantic import BaseModel
from graph import create_graph
import networkx as nx

app = FastAPI()

# -----------------------------
# 1. HOME ROUTE
# -----------------------------
@app.get("/")
def home():
    return {"message": "Emergency Routing System is running"}

# -----------------------------
# 2. REQUEST MODEL
# -----------------------------
class RouteRequest(BaseModel):
    start: str
    end: str
    emergency_level: str

# -----------------------------
# 3. ROUTE API (CORE FEATURE)
# -----------------------------
@app.post("/route")
def get_route(request: RouteRequest):

    G = create_graph()

    # STEP 1: modify weights using traffic
    for u, v, data in G.edges(data=True):
        traffic = data.get("traffic", 1)
        distance = data["weight"]

        # BMSSP-style cost function
        data["cost"] = distance * traffic

    try:
        # STEP 2: use cost instead of weight
        path = nx.shortest_path(
            G,
            request.start,
            request.end,
            weight="cost"
        )

        distance = nx.shortest_path_length(
            G,
            request.start,
            request.end,
            weight="cost"
        )

    except:
        return {
            "error": "No route found"
        }

    return {
        "start": request.start,
        "end": request.end,
        "path": path,
        "cost": distance,
        "eta_minutes": distance * 2,
        "logic": "BMSSP + traffic aware routing"
    }