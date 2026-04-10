from app.db import supabase


def get_latest_wind():
    response = (
        supabase
        .table("wind_fields")
        .select("*")
        .order("target_time_utc", desc=True)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


def get_wind_by_target_time(target_time_utc: str):
    response = (
        supabase
        .table("wind_fields")
        .select("*")
        .eq("target_time_utc", target_time_utc)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None