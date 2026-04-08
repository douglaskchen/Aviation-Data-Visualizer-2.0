def normalize_aircraft(raw: dict) -> dict:
    if not raw:
        return None

    icao24 = raw.get("hex")
    if not icao24:
        return None

    alt_baro_raw = raw.get("alt_baro")
    on_ground = alt_baro_raw == "ground"
    baro_altitude = None if on_ground else alt_baro_raw

    return {
        "icao24": raw.get("hex"),
        "callsign": (raw.get("flight") or "").strip() or None,
        "source_type": raw.get("type"),
        "registration": raw.get("r"),
        "aircraft_type": raw.get("t"),

        "latitude": raw.get("lat"),
        "longitude": raw.get("lon"),
        "true_track": raw.get("track"),
        "ground_speed": raw.get("gs"),

        "onground": on_ground,
        "baro_altitude": baro_altitude,
        "geo_altitude": raw.get("alt_geom"),
        "baro_vertical_rate": raw.get("baro_rate"),
        "geom_vertical_rate": raw.get("geom_rate"),

        "squawk": raw.get("squawk"),
        "emergency": raw.get("emergency"),
        "category": raw.get("category"),

        "seen": raw.get("seen"),
        "seen_pos": raw.get("seen_pos"),
        "rssi": raw.get("rssi"),
    }