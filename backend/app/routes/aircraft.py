from fastapi import APIRouter, Query
from app.services.aircraft_service import list_aircraft, list_aircraft_in_box

router = APIRouter(tags=["aircraft"])


@router.get("/aircraft")
def get_aircraft(
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lon: float | None = Query(default=None),
    max_lon: float | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
):
    if None not in (min_lat, max_lat, min_lon, max_lon):
        return list_aircraft_in_box(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )

    return list_aircraft(limit=limit)