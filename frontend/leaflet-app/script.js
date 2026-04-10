// const API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_URL = "https://aviation-data-visualizer-2-0.onrender.com"
const POLL_MS = 5000;
const MAX_AIRCRAFT = 500;

// animation tuning
const ANIMATION_DURATION_MS = 4000;
const MIN_ANIMATE_DISTANCE_METERS = 80;
const MAX_ANIMATE_DISTANCE_METERS = 50000;
const MAX_ANIMATED_MARKERS = 300;

// NEW: controls for new aircraft movement
const NEW_MARKER_TRAVEL_MS = 4000;
const NEW_MARKER_MIN_DISTANCE_METERS = 300;
const NEW_MARKER_MAX_DISTANCE_METERS = 3000;

const WORLD_BOUNDS = [
    [-85, -180],
    [85, 180]
];

const map = L.map("map", {
    center: [43.6532, -79.3832],
    zoom: 8,
    minZoom: 3,
    maxBounds: WORLD_BOUNDS,
    maxBoundsViscosity: 1.0,
    worldCopyJump: false
});

const osmLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 19,
    noWrap: true,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const aircraftLayer = L.layerGroup().addTo(map);

const baseLayers = {
    "OpenStreetMap": osmLayer
};

const overlayLayers = {
    "Aircraft": aircraftLayer
};

const layerControl = L.control.layers(baseLayers, overlayLayers).addTo(map);

const aircraftMarkers = new Map();
let windLayer = null;
let windOverlayRegistered = false;
let fetchInProgress = false;

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
    marker.addTo(aircraftLayer);

    marker._animationFrame = null;
    marker._lastHeading = heading;

    return marker;
}

function stopMarkerAnimation(marker) {
    if (marker._animationFrame) {
        cancelAnimationFrame(marker._animationFrame);
        marker._animationFrame = null;
    }
}

function lerp(start, end, t) {
    return start + (end - start) * t;
}

function distanceMeters(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const toRad = (deg) => deg * Math.PI / 180;

    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);

    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) ** 2;

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function animateMarkerTo(marker, targetLat, targetLon, durationMs) {
    stopMarkerAnimation(marker);

    const startLatLng = marker.getLatLng();
    const startLat = startLatLng.lat;
    const startLon = startLatLng.lng;
    const startTime = performance.now();

    function step(now) {
        const elapsed = now - startTime;
        const t = Math.min(elapsed / durationMs, 1);

        const nextLat = lerp(startLat, targetLat, t);
        const nextLon = lerp(startLon, targetLon, t);

        marker.setLatLng([nextLat, nextLon]);

        if (t < 1) {
            marker._animationFrame = requestAnimationFrame(step);
        } else {
            marker._animationFrame = null;
            marker.setLatLng([targetLat, targetLon]);
        }
    }

    marker._animationFrame = requestAnimationFrame(step);
}

// NEW: compute fake "previous position" for new aircraft
function computeSpawnOffset(lat, lon, aircraft) {
    const speed = aircraft.ground_speed ?? 0; // knots
    const heading = aircraft.true_track ?? 0;

    if (!speed || !heading) return [lat, lon];

    const speed_mps = speed * 0.514444;

    let distance = speed_mps * (NEW_MARKER_TRAVEL_MS / 1000);
    distance = Math.max(NEW_MARKER_MIN_DISTANCE_METERS, Math.min(distance, NEW_MARKER_MAX_DISTANCE_METERS));

    const headingRad = (heading * Math.PI) / 180;

    const dLat = -(distance * Math.cos(headingRad)) / 111320;
    const dLon = -(distance * Math.sin(headingRad)) / (111320 * Math.cos(lat * Math.PI / 180));

    return [lat + dLat, lon + dLon];
}

function updateMarker(marker, lat, lon, aircraft, shouldAnimate = true) {
    const heading = aircraft.true_track ?? 0;
    const currentLatLng = marker.getLatLng();
    const moveDistance = distanceMeters(currentLatLng.lat, currentLatLng.lng, lat, lon);

    marker.setRotationAngle(heading - 45);
    marker.setPopupContent(buildPopupHtml(aircraft));
    marker._lastHeading = heading;

    const shouldSkipAnimation =
        !shouldAnimate ||
        moveDistance < MIN_ANIMATE_DISTANCE_METERS ||
        moveDistance > MAX_ANIMATE_DISTANCE_METERS;

    if (shouldSkipAnimation) {
        stopMarkerAnimation(marker);
        marker.setLatLng([lat, lon]);
        return;
    }

    animateMarkerTo(marker, lat, lon, ANIMATION_DURATION_MS);
}

function removeStaleMarkers(seenIds) {
    for (const [aircraftId, marker] of aircraftMarkers.entries()) {
        if (!seenIds.has(aircraftId)) {
            stopMarkerAnimation(marker);
            aircraftLayer.removeLayer(marker);
            aircraftMarkers.delete(aircraftId);
        }
    }
}

function syncAircraftMarkers(aircraftList) {
    const seenIds = new Set();

    const animateThisCycle = aircraftList.length <= MAX_ANIMATED_MARKERS;

    aircraftList.forEach((aircraft) => {
        const lat = getAircraftLat(aircraft);
        const lon = getAircraftLon(aircraft);

        if (lat == null || lon == null) return;

        const aircraftId = getAircraftId(aircraft);
        seenIds.add(aircraftId);

        const existingMarker = aircraftMarkers.get(aircraftId);

        if (existingMarker) {
            updateMarker(existingMarker, lat, lon, aircraft, animateThisCycle);
        } else {
            const [spawnLat, spawnLon] = computeSpawnOffset(lat, lon, aircraft);

            const marker = createMarker(spawnLat, spawnLon, aircraft);
            aircraftMarkers.set(aircraftId, marker);

            // animate new marker into position
            animateMarkerTo(marker, lat, lon, NEW_MARKER_TRAVEL_MS);
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

async function fetchWind() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/wind`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const windRow = await response.json();
        const velocityData = windRow.payload_json;

        if (!Array.isArray(velocityData) || velocityData.length === 0) {
            throw new Error("Wind payload is empty or invalid.");
        }

        if (windLayer) {
            map.removeLayer(windLayer);
            if (windOverlayRegistered) {
                layerControl.removeLayer(windLayer);
                windOverlayRegistered = false;
            }
        }

        windLayer = L.velocityLayer({
            data: velocityData,
            displayValues: true,
            displayOptions: {
                velocityType: "Wind",
                position: "bottomleft",
                emptyString: "No wind data"
            }
        });

        layerControl.addOverlay(windLayer, "Wind");
        windOverlayRegistered = true;

        windLayer.addTo(map);

        console.log("Wind layer added.");
    } catch (error) {
        console.error("Failed to fetch wind:", error);
    }
}

fetchAircraft();
fetchWind();

setInterval(fetchAircraft, POLL_MS);
// uncomment later if decide to use wind poll instead of cron job
// setInterval(fetchWind, POLL_MS);

map.on("moveend", fetchAircraft);
map.on("zoomend", fetchAircraft);