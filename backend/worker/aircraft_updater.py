import time
import traceback
from datetime import datetime, timezone, timedelta

from app.db import supabase
from app.config import settings
from worker.aircraft_fetcher import fetch_aircraft
from worker.aircraft_normalizer import normalize_aircraft


STALE_SECONDS = getattr(settings, "aircraft_stale_seconds", 180)


def upsert_aircraft_rows(rows: list[dict]) -> None:
    if not rows:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    for row in rows:
        row["updated_at"] = now_iso

    supabase.table("aircraft_states").upsert(rows).execute()


def delete_stale_aircraft() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    cutoff_iso = cutoff.isoformat()

    response = (
        supabase
        .table("aircraft_states")
        .delete()
        .lt("updated_at", cutoff_iso)
        .execute()
    )

    if getattr(response, "data", None):
        return len(response.data)

    return 0


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

    # 🔥 NEW: cleanup stale rows
    deleted = delete_stale_aircraft()

    print(f"Upserted {len(normalized_rows)} rows | Deleted {deleted} stale rows")

    return len(normalized_rows)


def main() -> None:
    print("Starting aircraft updater...")

    while True:
        try:
            run_once()
        except Exception as exc:
            print(f"Updater error: {exc}")
            traceback.print_exc()

        time.sleep(settings.aircraft_poll_seconds)


if __name__ == "__main__":
    main()