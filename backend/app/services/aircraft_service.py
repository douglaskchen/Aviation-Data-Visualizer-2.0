from app.db import supabase


def list_aircraft(limit: int = 500):
    response = (
        supabase
        .table("aircraft_states")
        .select("*")
        .not_.is_("latitude", "null")
        .not_.is_("longitude", "null")
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def list_aircraft_in_box(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    limit: int = 1000,
):
    response = (
        supabase
        .table("aircraft_states")
        .select("*")
        .not_.is_("latitude", "null")
        .not_.is_("longitude", "null")
        .gte("latitude", min_lat)
        .lte("latitude", max_lat)
        .gte("longitude", min_lon)
        .lte("longitude", max_lon)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data