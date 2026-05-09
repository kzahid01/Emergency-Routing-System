from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.routing import calculate_route

app = FastAPI()


class RouteRequest(BaseModel):
    start: int
    end: int
    emergency_level: str = "medium"


@app.post("/route")
def get_route(request: RouteRequest):

    result = calculate_route(
        request.start,
        request.end,
        request.emergency_level
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result