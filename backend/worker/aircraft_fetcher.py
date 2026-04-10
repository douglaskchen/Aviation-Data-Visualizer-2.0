import httpx
from app.config import settings


def fetch_aircraft(
    lat: float | None = None,
    lon: float | None = None,
    radius_nm: int | None = None,
) -> list[dict]:
    lat = lat if lat is not None else settings.default_lat
    lon = lon if lon is not None else settings.default_lon
    radius_nm = radius_nm if radius_nm is not None else settings.default_radius_nm

    url = f"{settings.airplanes_base_url}/point/{lat}/{lon}/{radius_nm}"
    # print(f"Fetching aircraft from: {url}")

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(url)
        # print(f"Status code: {response.status_code}")
        # print(f"Response text preview: {response.text[:300]}")
        response.raise_for_status()
        payload = response.json()

    aircraft = payload.get("ac", [])
    return aircraft if isinstance(aircraft, list) else []