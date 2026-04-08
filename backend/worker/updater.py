import time
import traceback
from datetime import datetime, timezone

from app.db import supabase
from app.config import settings
from worker.aircraft_data_fetcher import fetch_aircraft
from worker.normalizers import normalize_aircraft


def upsert_aircraft_rows(rows: list[dict]) -> None:
    if not rows:
        return

    # add/update timestamp before upsert
    now_iso = datetime.now(timezone.utc).isoformat()
    for row in rows:
        row["updated_at"] = now_iso

    supabase.table("aircraft_states").upsert(rows).execute()


def run_once() -> int:
    raw_aircraft = fetch_aircraft()
    normalized_rows = []

    for raw in raw_aircraft:
        row = normalize_aircraft(raw)
        if not row:
            continue
        # basic filters
        if row.get("latitude") is None or row.get("longitude") is None:
            continue
        if row.get("icao24") is None:
            continue
        normalized_rows.append(row)

    upsert_aircraft_rows(normalized_rows)
    return len(normalized_rows)


def main() -> None:
    print("Starting aircraft updater...")

    while True:
        try:
            count = run_once()
            print(f"Upserted {count} aircraft rows.")
        except Exception as exc:
            print(f"Updater error: {exc}")
            traceback.print_exc()

        time.sleep(settings.aircraft_poll_seconds)


if __name__ == "__main__":
    main()