from fastapi import FastAPI
from models import RouteRequest
from routing import calculate_route

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "Emergency Routing System is running"
    }

@app.post("/route")
def get_route(request: RouteRequest):

    try:
        path, distance = calculate_route(
            request.start,
            request.end
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