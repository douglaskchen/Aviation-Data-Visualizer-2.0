import traceback
from datetime import datetime, timezone

from app.db import supabase
from worker.wind_fetcher import fetch_wind
from worker.wind_normalizer import normalize_wind


def upsert_wind_row(row: dict) -> None:
    if not row:
        raise ValueError("Cannot upsert empty wind row.")

    # optional audit/update timestamp for later
    # row["updated_at"] = datetime.now(timezone.utc).isoformat()

    (
        supabase
        .table("wind_fields")
        .upsert(
            row,
            on_conflict="model,product,target_time_utc",
        )
        .execute()
    )


def run_once() -> dict:
    fetch_result = fetch_wind()
    row = normalize_wind(fetch_result)
    upsert_wind_row(row)

    print(
        f"Upserted wind row | "
        f"target_time_utc={row.get('target_time_utc')} | "
        f"source_kind={row.get('source_kind')} | "
        f"record_count={row.get('record_count')}"
    )

    return row


if __name__ == "__main__":
    try:
        run_once()
    except Exception as exc:
        print(f"Wind updater error: {exc}")
        traceback.print_exc()
        raise