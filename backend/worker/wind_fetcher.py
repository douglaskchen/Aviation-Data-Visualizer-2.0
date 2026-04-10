import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


GFS_BASE_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl"


def floor_to_3h(dt: datetime) -> datetime:
    hour = (dt.hour // 3) * 3
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0)


def floor_to_6h(dt: datetime) -> datetime:
    hour = (dt.hour // 6) * 6
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0)


def build_anl_url(cycle_dt: datetime) -> str:
    date_str = cycle_dt.strftime("%Y%m%d")
    hour_str = cycle_dt.strftime("%H")

    return (
        f"{GFS_BASE_URL}"
        f"?dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
        f"&file=gfs.t{hour_str}z.pgrb2.1p00.anl"
        f"&var_UGRD=on"
        f"&var_VGRD=on"
        f"&lev_20_m_above_ground=on"
        f"&subregion="
        f"&leftlon=0"
        f"&rightlon=360"
        f"&toplat=90"
        f"&bottomlat=-90"
    )


def build_forecast_url(base_cycle_dt: datetime, forecast_hour: int) -> str:
    date_str = base_cycle_dt.strftime("%Y%m%d")
    hour_str = base_cycle_dt.strftime("%H")
    forecast_str = f"{forecast_hour:03d}"

    return (
        f"{GFS_BASE_URL}"
        f"?dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
        f"&file=gfs.t{hour_str}z.pgrb2.1p00.f{forecast_str}"
        f"&var_UGRD=on"
        f"&var_VGRD=on"
        f"&lev_20_m_above_ground=on"
        f"&subregion="
        f"&leftlon=0"
        f"&rightlon=360"
        f"&toplat=90"
        f"&bottomlat=-90"
    )


def build_candidate_urls(target_dt: datetime) -> list[tuple[str, str]]:
    """
    Return candidate URLs in priority order.

    Rules:
    - For 6-hour targets (00/06/12/18):
        1) target anl
        2) previous 6-hour cycle forecast to target
    - For 3-hour in-between targets (03/09/15/21):
        1) nearest previous 6-hour cycle forecast
        2) 6 hours older cycle forecast
    """
    candidates: list[tuple[str, str]] = []

    if target_dt.hour % 6 == 0:
        prev_cycle = target_dt - timedelta(hours=6)

        candidates.append(("analysis", build_anl_url(target_dt)))
        candidates.append(("prev_cycle_forecast", build_forecast_url(prev_cycle, 6)))
        return candidates

    nearest_prev_cycle = floor_to_6h(target_dt)
    older_cycle = nearest_prev_cycle - timedelta(hours=6)

    first_forecast_hour = int((target_dt - nearest_prev_cycle).total_seconds() // 3600)
    second_forecast_hour = int((target_dt - older_cycle).total_seconds() // 3600)

    candidates.append(
        (f"forecast_from_{nearest_prev_cycle.strftime('%HZ')}", build_forecast_url(nearest_prev_cycle, first_forecast_hour))
    )
    candidates.append(
        (f"forecast_from_{older_cycle.strftime('%HZ')}", build_forecast_url(older_cycle, second_forecast_hour))
    )

    return candidates


def download_first_available(url_candidates: list[tuple[str, str]], output_path: Path) -> tuple[str, str]:
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        for source_kind, url in url_candidates:
            print(f"Trying {source_kind}: {url}")

            try:
                response = client.get(url)

                print(f"Status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type')}")

                if response.status_code != 200:
                    preview = response.text[:500] if response.text else ""
                    print(f"HTTP {response.status_code} for {source_kind}")
                    print(preview)
                    continue

                output_path.write_bytes(response.content)
                size = output_path.stat().st_size if output_path.exists() else 0

                print(f"Downloaded bytes: {size}")

                if size == 0:
                    preview = response.text[:500] if response.text else ""
                    print(f"Empty response body for {source_kind}")
                    print(preview)
                    continue

                # Detect HTML error pages pretending to be successful downloads
                prefix = response.content[:200].decode("utf-8", errors="ignore").lower()
                if "<html" in prefix or "<!doctype html" in prefix:
                    print(f"Received HTML instead of GRIB2 for {source_kind}")
                    print(response.text[:500])
                    continue

                print(f"Success: {source_kind}")
                return source_kind, url

            except Exception as exc:
                print(f"Failed {source_kind}: {exc}")

    raise RuntimeError("No candidate GFS URL succeeded.")


def convert_grib2_to_json(grib2_path: Path, json_path: Path) -> None:
    command = [
        "grib2json",
        "-d",
        "-n",
        "-o",
        str(json_path),
        str(grib2_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    print(f"grib2json return code: {result.returncode}")
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError("grib2json conversion failed.")

    if not json_path.exists() or json_path.stat().st_size == 0:
        raise RuntimeError("JSON output file is missing or empty.")


def load_json(json_path: Path) -> list[dict]:
    with json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list from grib2json, got {type(payload).__name__}")

    return payload


def fetch_wind(
    target_dt: datetime | None = None,
    grib2_path: str = "winddata.grib2",
    json_path: str = "winddata.json",
) -> dict:
    """
    Fetch wind data for the latest passed 3-hour UTC target.

    Examples:
    - 06Z -> try:
        1) 06Z anl
        2) 00Z f006

    - 09Z -> try:
        1) 06Z f003
        2) 00Z f009
    """
    if target_dt is None:
        target_dt = floor_to_3h(datetime.now(timezone.utc))

    grib2_file = Path(grib2_path)
    json_file = Path(json_path)

    candidates = build_candidate_urls(target_dt)
    source_kind, source_url = download_first_available(candidates, grib2_file)

    convert_grib2_to_json(grib2_file, json_file)
    payload = load_json(json_file)

    return {
        "target_time_utc": target_dt.isoformat(),
        "source_kind": source_kind,
        "source_url": source_url,
        "payload": payload,
    }


if __name__ == "__main__":
    result = fetch_wind()
    print(f"Fetched {len(result['payload'])} records")
    print(f"Source kind: {result['source_kind']}")
    print(f"Source URL: {result['source_url']}")