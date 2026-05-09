from typing import Literal

from pydantic import BaseModel, Field


EmergencyLevel = Literal["low", "medium", "critical"]


class RouteRequest(BaseModel):
    # Graph node IDs are modeled as non-negative integers in this system.
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)

    # Reject unknown emergency levels with 422 (FastAPI/Pydantic validation).
    emergency_level: EmergencyLevel = "medium"
