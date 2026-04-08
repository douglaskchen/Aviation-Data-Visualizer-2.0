import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")

    airplanes_base_url: str = os.getenv("AIRPLANES_BASE_URL", "https://api.airplanes.live/v2")
    aircraft_poll_seconds: int = int(os.getenv("AIRCRAFT_POLL_SECONDS", "10"))

    # GTA-ish default center/radius example
    default_lat: float = float(os.getenv("DEFAULT_LAT", "43.6532"))
    default_lon: float = float(os.getenv("DEFAULT_LON", "-79.3832"))
    default_radius_nm: int = int(os.getenv("DEFAULT_RADIUS_NM", "150"))


settings = Settings()