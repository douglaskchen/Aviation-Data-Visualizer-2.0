from fastapi import FastAPI
from app.routes import health, aircraft

app = FastAPI(title="AvDataVis API")

app.include_router(health.router, prefix="/api")
app.include_router(aircraft.router, prefix="/api")