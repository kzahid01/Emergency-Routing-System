from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException

from backend.models import (
    AutoDispatchRequest
)

from backend.routing import (
    calculate_emergency_dispatch
)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():

    return {
        "message":
        "Emergency Routing API Running"
    }


@app.post("/auto-dispatch")
def auto_dispatch(
    request: AutoDispatchRequest
):

    try:

        result = (
            calculate_emergency_dispatch(
                request.emergency_lat,
                request.emergency_lon,
                request.emergency_level
            )
        )

        if "error" in result:

            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )