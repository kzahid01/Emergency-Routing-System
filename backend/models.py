from pydantic import BaseModel


class AutoDispatchRequest(BaseModel):
    emergency_lat: float
    emergency_lon: float
    emergency_level: str = "critical"