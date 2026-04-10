from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import health, aircraft, wind

app = FastAPI(title="AvDataVis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(aircraft.router, prefix="/api")
app.include_router(wind.router, prefix="/api")