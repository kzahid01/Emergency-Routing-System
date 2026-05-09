from fastapi import FastAPI
from backend.models import RouteRequest
from backend.routing import calculate_route

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "Emergency Routing System is running"
    }

@app.post("/route")
def get_route(request: RouteRequest):

    try:
        result = calculate_route(request.start)

        return result

    except Exception as e:

        return {
            "error": str(e)
        }