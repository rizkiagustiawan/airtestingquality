"""
AERMOD Dispersion Simulator.
Simplified Gaussian plume model producing GeoJSON concentration contours
for visualization on a Leaflet map.
"""

import math
from emission_sources import get_source_by_id, EMISSION_SOURCES


# Pasquill-Gifford dispersion coefficients (σy, σz as functions of downwind distance)
# σ = a * x^b  (x in km, σ in m)
PG_COEFFICIENTS = {
    "A": {"sy_a": 209.6, "sy_b": 0.8804, "sz_a": 417.9, "sz_b": 2.0586},
    "B": {"sy_a": 154.7, "sy_b": 0.8932, "sz_a": 109.3, "sz_b": 1.0971},
    "C": {"sy_a": 103.3, "sy_b": 0.9112, "sz_a": 61.14, "sz_b": 0.9115},
    "D": {"sy_a": 68.28, "sy_b": 0.9112, "sz_a": 30.37, "sz_b": 0.7370},
    "E": {"sy_a": 51.05, "sy_b": 0.9112, "sz_a": 21.62, "sz_b": 0.6794},
    "F": {"sy_a": 33.96, "sy_b": 0.9112, "sz_a": 14.35, "sz_b": 0.6020},
}


def _sigma_y(x_km: float, stability: str) -> float:
    """Lateral dispersion coefficient (m)."""
    c = PG_COEFFICIENTS.get(stability, PG_COEFFICIENTS["D"])
    return c["sy_a"] * (x_km ** c["sy_b"])


def _sigma_z(x_km: float, stability: str) -> float:
    """Vertical dispersion coefficient (m)."""
    c = PG_COEFFICIENTS.get(stability, PG_COEFFICIENTS["D"])
    return c["sz_a"] * (x_km ** c["sz_b"])


def _gaussian_conc(
    q: float,         # emission rate (g/s)
    u: float,         # wind speed (m/s)
    x: float,         # downwind distance (m)
    y: float,         # crosswind distance (m)
    z: float,         # receptor height (m)
    h: float,         # effective stack height (m)
    stability: str
) -> float:
    """Calculate ground-level concentration (µg/m³) using Gaussian plume formula."""
    if x <= 0 or u <= 0.1:
        return 0.0

    x_km = x / 1000.0
    sy = _sigma_y(x_km, stability)
    sz = _sigma_z(x_km, stability)

    if sy <= 0 or sz <= 0:
        return 0.0

    # Gaussian plume equation with ground reflection
    exp_y = math.exp(-(y ** 2) / (2 * sy ** 2))
    exp_z1 = math.exp(-((z - h) ** 2) / (2 * sz ** 2))
    exp_z2 = math.exp(-((z + h) ** 2) / (2 * sz ** 2))

    conc = (q * 1e6) / (2 * math.pi * u * sy * sz) * exp_y * (exp_z1 + exp_z2)
    return conc


def compute_dispersion_grid(
    source_id: str = "smelter-stack",
    wind_dir: float = 230.0,       # deg, direction wind is blowing FROM
    wind_speed: float = 3.5,       # m/s
    stability: str = "C",
    grid_size_m: float = 10000,    # total grid extent (m)
    resolution: int = 40           # grid cells per side
) -> dict:
    """
    Compute a concentration grid for a single source and return as GeoJSON polygons
    with concentration bands suitable for Leaflet rendering.
    """
    source = get_source_by_id(source_id)
    if source is None:
        source = EMISSION_SOURCES[2]  # fallback to smelter

    src_lat = source["lat"]
    src_lon = source["lon"]
    stack_h = source.get("stack_height_m", 0)
    pollutant = "pm10"
    q = source["emissions"].get(pollutant, 1.0)

    # Effective stack height (simplified plume rise for point sources)
    effective_h = stack_h
    if source["type"] == "point":
        v_s = source.get("exit_velocity_ms", 10)
        d = source.get("stack_diameter_m", 2)
        delta_h = (1.6 * (v_s * d) ** (1/3) * (3.5 * wind_speed) ** (2/3)) / max(wind_speed, 0.5)
        effective_h = stack_h + min(delta_h, 200)

    # Wind direction: convert "from" to "towards" (add 180°)
    wind_towards_deg = (wind_dir + 180) % 360
    wind_rad = math.radians(wind_towards_deg)

    # Lat/Lon per meter (approximate at -8.8°)
    lat_per_m = 1 / 111320.0
    lon_per_m = 1 / (111320.0 * math.cos(math.radians(src_lat)))

    # Build concentration grid
    half = grid_size_m / 2
    step = grid_size_m / resolution
    grid = []

    for i in range(resolution):
        for j in range(resolution):
            # Grid point in m relative to source
            gx = (j + 0.5) * step - half
            gy = (i + 0.5) * step - half

            # Rotate into wind-aligned coordinates
            # x = downwind, y = crosswind
            cos_w = math.cos(wind_rad)
            sin_w = math.sin(wind_rad)
            downwind = gx * sin_w + gy * cos_w
            crosswind = gx * cos_w - gy * sin_w

            conc = _gaussian_conc(q, wind_speed, downwind, crosswind, 0, effective_h, stability)
            
            if conc > 0.5:  # threshold to avoid noise
                cell_lat = src_lat + gy * lat_per_m
                cell_lon = src_lon + gx * lon_per_m
                grid.append({
                    "lat": cell_lat,
                    "lon": cell_lon,
                    "conc": round(conc, 2)
                })

    # Convert grid to GeoJSON features with concentration bands
    bands = [
        {"min": 0.5, "max": 10, "color": "#10B981", "opacity": 0.15, "label": "< 10 µg/m³ (Low)"},
        {"min": 10, "max": 50, "color": "#3B82F6", "opacity": 0.25, "label": "10-50 µg/m³ (Moderate)"},
        {"min": 50, "max": 75, "color": "#F59E0B", "opacity": 0.35, "label": "50-75 µg/m³ (PP22 Limit)"},
        {"min": 75, "max": 150, "color": "#EF4444", "opacity": 0.45, "label": "75-150 µg/m³ (Exceed)"},
        {"min": 150, "max": 99999, "color": "#7C2D12", "opacity": 0.55, "label": "> 150 µg/m³ (Critical)"},
    ]

    features = []
    cell_half_lat = (step / 2) * lat_per_m
    cell_half_lon = (step / 2) * lon_per_m

    for pt in grid:
        band = None
        for b in bands:
            if b["min"] <= pt["conc"] < b["max"]:
                band = b
                break
        if band is None:
            continue

        # Create cell polygon
        coords = [[
            [pt["lon"] - cell_half_lon, pt["lat"] - cell_half_lat],
            [pt["lon"] + cell_half_lon, pt["lat"] - cell_half_lat],
            [pt["lon"] + cell_half_lon, pt["lat"] + cell_half_lat],
            [pt["lon"] - cell_half_lon, pt["lat"] + cell_half_lat],
            [pt["lon"] - cell_half_lon, pt["lat"] - cell_half_lat],
        ]]

        features.append({
            "type": "Feature",
            "properties": {
                "concentration": pt["conc"],
                "color": band["color"],
                "opacity": band["opacity"],
                "band_label": band["label"]
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": coords
            }
        })

    return {
        "type": "FeatureCollection",
        "source": source["name"],
        "source_id": source["id"],
        "pollutant": pollutant,
        "wind_dir": wind_dir,
        "wind_speed": wind_speed,
        "stability": stability,
        "effective_height_m": round(effective_h, 1),
        "bands": bands,
        "features": features
    }
