from pydantic import BaseModel

class RouteRequest(BaseModel):
    start: str
    end: str
    emergency_level: str