from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "backend working"}

@app.post("/route")
def get_route():
    return {"message": "route working"}