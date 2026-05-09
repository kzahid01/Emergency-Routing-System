from pydantic import BaseModel

class RouteRequest(BaseModel):
    start: int
    end: int
    emergency_level: str