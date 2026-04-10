from fastapi import APIRouter, HTTPException, Query
from app.services.wind_service import get_latest_wind, get_wind_by_target_time

router = APIRouter(tags=["wind"])


@router.get("/wind")
def get_wind(target_time_utc: str | None = Query(default=None)):
    if target_time_utc:
        row = get_wind_by_target_time(target_time_utc)
        if not row:
            raise HTTPException(status_code=404, detail="Wind data not found for target_time_utc.")
        return row

    row = get_latest_wind()
    if not row:
        raise HTTPException(status_code=404, detail="No wind data found.")

    return row