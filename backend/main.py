
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to OmniSight!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "project": "OmniSight"}


from pydantic import BaseModel, HttpUrl

class InspectRequest(BaseModel):
    url: HttpUrl


@app.post("/inspect")
def inspect_website(request: InspectRequest):
    return {
        "message": "Website URL received successfully",
        "url": str(request.url),
        "status": "inspection_requested",
    }

