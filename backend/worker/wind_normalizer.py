def normalize_wind(fetch_result: dict) -> dict:
    if not fetch_result:
        raise ValueError("Missing fetch_result.")

    payload = fetch_result.get("payload")
    if not isinstance(payload, list):
        raise ValueError("Wind payload must be a list.")

    if len(payload) == 0:
        raise ValueError("Wind payload is empty.")

    parameter_names = []
    for record in payload:
        header = record.get("header", {})
        parameter_names.append(header.get("parameterNumberName"))

    return {
        "source": "NOAA NOMADS",
        "model": "GFS",
        "product": "wind_20m",
        "target_time_utc": fetch_result.get("target_time_utc"),
        "source_kind": fetch_result.get("source_kind"),
        "source_url": fetch_result.get("source_url"),
        "record_count": len(payload),
        "payload_json": payload,
    }