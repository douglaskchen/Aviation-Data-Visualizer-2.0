const API_BASE_URL = "http://127.0.0.1:8000";
const POLL_MS = 10000;
const MAX_AIRCRAFT = 1000;

const map = L.map("map").setView([43.6532, -79.3832], 8);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const aircraftMarkers = new Map();

const planeIcon = L.icon({
    iconUrl: "planeicon.png",
    iconSize: [33, 20],
    iconAnchor: [16, 10],
    popupAnchor: [0, -10]
});

function formatValue(value, fallback = "N/A") {
    return value === null || value === undefined || value === "" ? fallback : value;
}

function formatHeading(value) {
    if (value === null || value === undefined || value === "") return "N/A";
    return `${Math.round(value)}°`;
}

function formatSpeed(value) {
    if (value === null || value === undefined || value === "") return "N/A";
    return `${Math.round(value)} kt`;
}

function formatAltitude(value) {
    if (value === null || value === undefined || value === "") return "N/A";
    return `${Math.round(value)} ft`;
}

function getAircraftId(aircraft) {
    return aircraft.icao24 || `${aircraft.callsign || "unknown"}-${aircraft.registration || "unknown"}`;
}

function getAircraftLat(aircraft) {
    return aircraft.latitude;
}

function getAircraftLon(aircraft) {
    return aircraft.longitude;
}

function buildPopupHtml(aircraft) {
    const callsign = formatValue(aircraft.callsign, "Unknown");
    const registration = formatValue(aircraft.registration);
    const aircraftType = formatValue(aircraft.aircraft_type);
    const heading = formatHeading(aircraft.true_track);
    const speed = formatSpeed(aircraft.ground_speed);
    const altitude = formatAltitude(aircraft.baro_altitude);
    const updatedAt = formatValue(aircraft.updated_at);
    const onGround = aircraft.onground === true ? "Yes" : "No";

    return `
    <b>${callsign}</b><br>
    Registration: ${registration}<br>
    Type: ${aircraftType}<br>
    Heading: ${heading}<br>
    Speed: ${speed}<br>
    Altitude: ${altitude}<br>
    On Ground: ${onGround}<br>
    Updated: ${updatedAt}
  `;
}

function createMarker(lat, lon, aircraft) {
    const heading = aircraft.true_track ?? 0;

    const marker = L.marker([lat, lon], {
        icon: planeIcon,
        rotationAngle: heading - 45
    });

    marker.bindPopup(buildPopupHtml(aircraft));
    marker.addTo(map);
    return marker;
}

function updateMarker(marker, lat, lon, aircraft) {
    const heading = aircraft.true_track ?? 0;

    marker.setLatLng([lat, lon]);
    marker.setRotationAngle(heading - 45);
    marker.setPopupContent(buildPopupHtml(aircraft));
}

function removeStaleMarkers(seenIds) {
    for (const [aircraftId, marker] of aircraftMarkers.entries()) {
        if (!seenIds.has(aircraftId)) {
            map.removeLayer(marker);
            aircraftMarkers.delete(aircraftId);
        }
    }
}

function syncAircraftMarkers(aircraftList) {
    const seenIds = new Set();

    aircraftList.forEach((aircraft) => {
        const lat = getAircraftLat(aircraft);
        const lon = getAircraftLon(aircraft);

        if (lat == null || lon == null) return;

        const aircraftId = getAircraftId(aircraft);
        seenIds.add(aircraftId);

        const existingMarker = aircraftMarkers.get(aircraftId);

        if (existingMarker) {
            updateMarker(existingMarker, lat, lon, aircraft);
        } else {
            const marker = createMarker(lat, lon, aircraft);
            aircraftMarkers.set(aircraftId, marker);
        }
    });

    removeStaleMarkers(seenIds);
}

function buildAircraftUrl() {
    const bounds = map.getBounds();

    const url = new URL(`${API_BASE_URL}/api/aircraft`);
    url.searchParams.set("min_lat", bounds.getSouth());
    url.searchParams.set("max_lat", bounds.getNorth());
    url.searchParams.set("min_lon", bounds.getWest());
    url.searchParams.set("max_lon", bounds.getEast());
    url.searchParams.set("limit", MAX_AIRCRAFT);

    return url.toString();
}

let fetchInProgress = false;

async function fetchAircraft() {
    if (fetchInProgress) return;
    fetchInProgress = true;

    try {
        const response = await fetch(buildAircraftUrl());

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const aircraftList = await response.json();
        console.log("Aircraft response:", aircraftList);
        syncAircraftMarkers(aircraftList);
    } catch (error) {
        console.error("Failed to fetch aircraft:", error);
    } finally {
        fetchInProgress = false;
    }
}

fetchAircraft();
setInterval(fetchAircraft, POLL_MS);
map.on("moveend", fetchAircraft);
map.on("zoomend", fetchAircraft);