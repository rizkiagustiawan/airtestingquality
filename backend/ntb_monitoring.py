"""
NTB Regional Air Quality Monitoring System.

Provides comprehensive air quality monitoring across Nusa Tenggara Barat (NTB)
with spatial interpolation, regional station registry, and multi-source data integration.

Covers:
- Lombok: Mataram, Lombok Barat, Lombok Tengah, Lombok Timur, Lombok Utara
- Sumbawa: Sumbawa, Sumbawa Barat, Dompu, Bima, Kota Bima
"""

import math
from datetime import datetime, timezone

import numpy as np

# ============================================================
# NTB STATION REGISTRY
# ============================================================
# Real coordinates of monitoring stations across NTB
NTB_STATIONS = [
    # Lombok Island
    {
        "id": "ntb-01",
        "name": "Mataram Central",
        "city": "Mataram",
        "island": "Lombok",
        "lat": -8.5833,
        "lon": 116.1167,
        "type": "urban",
        "description": "Kota Mataram - ibukota NTB",
    },
    {
        "id": "ntb-02",
        "name": "Lombok International Airport",
        "city": "Lombok Tengah",
        "island": "Lombok",
        "lat": -8.7610,
        "lon": 116.2750,
        "type": "airport",
        "description": "Bandara Internasional Lombok",
    },
    {
        "id": "ntb-03",
        "name": "Senggigi Tourism Area",
        "city": "Lombok Barat",
        "island": "Lombok",
        "lat": -8.4917,
        "lon": 116.0417,
        "type": "tourism",
        "description": "Kawasan wisata Senggigi",
    },
    {
        "id": "ntb-04",
        "name": "Tanjung Industrial Zone",
        "city": "Lombok Utara",
        "island": "Lombok",
        "lat": -8.3833,
        "lon": 116.1500,
        "type": "industrial",
        "description": "Kawasan industri Tanjung",
    },
    {
        "id": "ntb-05",
        "name": "Praya Urban",
        "city": "Lombok Tengah",
        "island": "Lombok",
        "lat": -8.7050,
        "lon": 116.2700,
        "type": "urban",
        "description": "Kota Praya - Lombok Tengah",
    },
    {
        "id": "ntb-06",
        "name": "Selong East Lombok",
        "city": "Lombok Timur",
        "island": "Lombok",
        "lat": -8.6500,
        "lon": 116.5333,
        "type": "urban",
        "description": "Kota Selong - Lombok Timur",
    },
    # Sumbawa Island
    {
        "id": "ntb-07",
        "name": "Sumbawa Barat (AMNT Area)",
        "city": "Sumbawa Barat",
        "island": "Sumbawa",
        "lat": -8.8250,
        "lon": 116.8400,
        "type": "mining",
        "description": "Kawasan pertambangan AMNT",
    },
    {
        "id": "ntb-08",
        "name": "Sumbawa Besar",
        "city": "Sumbawa",
        "island": "Sumbawa",
        "lat": -8.4833,
        "lon": 117.4167,
        "type": "urban",
        "description": "Kota Sumbawa Besar",
    },
    {
        "id": "ntb-09",
        "name": "Dompu Central",
        "city": "Dompu",
        "island": "Sumbawa",
        "lat": -8.5333,
        "lon": 118.4667,
        "type": "urban",
        "description": "Kota Dompu",
    },
    {
        "id": "ntb-10",
        "name": "Bima Regional",
        "city": "Bima",
        "island": "Sumbawa",
        "lat": -8.4667,
        "lon": 118.7167,
        "type": "urban",
        "description": "Kota Bima",
    },
    {
        "id": "ntb-11",
        "name": "Bima Port Area",
        "city": "Bima",
        "island": "Sumbawa",
        "lat": -8.4500,
        "lon": 118.7333,
        "type": "port",
        "description": "Pelabuhan Bima",
    },
    {
        "id": "ntb-12",
        "name": "Tambora Volcano Area",
        "city": "Dompu",
        "island": "Sumbawa",
        "lat": -8.2500,
        "lon": 117.9500,
        "type": "rural",
        "description": "Kawasan Gunung Tambora",
    },
]


def get_all_stations() -> list[dict]:
    """Get all NTB monitoring stations."""
    return NTB_STATIONS.copy()


def get_stations_by_island(island: str) -> list[dict]:
    """Get stations filtered by island (Lombok/Sumbawa)."""
    return [s for s in NTB_STATIONS if s["island"].lower() == island.lower()]


def get_stations_by_type(station_type: str) -> list[dict]:
    """Get stations filtered by type (urban/industrial/mining/airport/etc)."""
    return [s for s in NTB_STATIONS if s["type"].lower() == station_type.lower()]


def get_station_by_id(station_id: str) -> dict | None:
    """Get station by ID."""
    for s in NTB_STATIONS:
        if s["id"] == station_id:
            return s
    return None


# ============================================================
# SPATIAL INTERPOLATION (IDW - Inverse Distance Weighting)
# ============================================================

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def idw_interpolate(
    station_data: list[dict],
    grid_resolution: float = 0.05,
    power: float = 2.0,
    max_distance_km: float = 100.0,
) -> dict:
    """
    Inverse Distance Weighting (IDW) spatial interpolation.

    Scientific basis:
    - Shepard (1968) "A two-dimensional interpolation function for irregularly-spaced data"
    - Standard method for air quality spatial interpolation

    Parameters:
    - station_data: list of {lat, lon, value} for each station
    - grid_resolution: grid cell size in degrees (~5km at NTB latitude)
    - power: IDW power parameter (2 = standard)
    - max_distance_km: maximum interpolation distance

    Returns: GeoJSON-compatible grid with interpolated values
    """
    if not station_data:
        return {"type": "FeatureCollection", "features": []}

    # NTB bounding box
    lats = [s["lat"] for s in station_data]
    lons = [s["lon"] for s in station_data]

    lat_min = min(lats) - 0.2
    lat_max = max(lats) + 0.2
    lon_min = min(lons) - 0.2
    lon_max = max(lons) + 0.2

    # Generate grid
    grid_points = []
    lat = lat_min
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            # IDW interpolation
            numerator = 0.0
            denominator = 0.0
            nearest_station = None
            nearest_dist = float("inf")

            for station in station_data:
                dist = _haversine_distance(lat, lon, station["lat"], station["lon"])

                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_station = station

                if dist < 0.001:  # Very close to station
                    numerator = station["value"]
                    denominator = 1.0
                    break

                if dist <= max_distance_km:
                    weight = 1.0 / (dist ** power)
                    numerator += weight * station["value"]
                    denominator += weight

            if denominator > 0:
                interpolated_value = numerator / denominator
            else:
                interpolated_value = 0.0

            grid_points.append({
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "value": round(interpolated_value, 2),
                "nearest_station": nearest_station["id"] if nearest_station else None,
                "distance_to_nearest_km": round(nearest_dist, 1),
            })

            lon += grid_resolution
        lat += grid_resolution

    return {
        "type": "grid",
        "bbox": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "resolution_deg": grid_resolution,
        "power": power,
        "max_distance_km": max_distance_km,
        "n_stations": len(station_data),
        "n_grid_points": len(grid_points),
        "grid": grid_points,
    }


def generate_ntb_heatmap(
    pollutant: str = "pm10",
    station_measurements: dict[str, dict] | None = None,
    grid_resolution: float = 0.05,
) -> dict:
    """
    Generate heatmap data for NTB region.

    Combines station data with IDW interpolation to create
    a continuous air quality surface across NTB.

    Parameters:
    - pollutant: which pollutant to map
    - station_measurements: {station_id: {pollutant: value}} dict
    - grid_resolution: grid cell size in degrees
    """
    # Default measurements if none provided
    if station_measurements is None:
        station_measurements = {}
        for station in NTB_STATIONS:
            base_val = {"pm10": 45, "pm25": 15, "so2": 18, "no2": 12, "co": 800}.get(pollutant, 30)
            # Add spatial variation based on location
            if station["type"] == "mining":
                val = base_val * 1.5
            elif station["type"] == "industrial":
                val = base_val * 1.3
            elif station["type"] == "urban":
                val = base_val * 1.1
            elif station["type"] == "rural":
                val = base_val * 0.7
            else:
                val = base_val

            # Add noise
            val += np.random.normal(0, val * 0.1)
            station_measurements[station["id"]] = {pollutant: max(1, round(val, 2))}

    # Prepare station data for interpolation
    station_data = []
    for station in NTB_STATIONS:
        if station["id"] in station_measurements:
            val = station_measurements[station["id"]].get(pollutant)
            if val is not None:
                station_data.append({
                    "id": station["id"],
                    "name": station["name"],
                    "lat": station["lat"],
                    "lon": station["lon"],
                    "value": float(val),
                })

    # Run IDW interpolation
    grid = idw_interpolate(station_data, grid_resolution=grid_resolution)

    # Compute regional statistics
    values = [p["value"] for p in grid["grid"] if p["value"] > 0]
    station_values = [s["value"] for s in station_data]

    return {
        "pollutant": pollutant,
        "unit": "ug/m3",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "stations": station_data,
        "grid": grid,
        "regional_stats": {
            "station_mean": round(float(np.mean(station_values)), 2) if station_values else 0,
            "station_max": round(float(np.max(station_values)), 2) if station_values else 0,
            "station_min": round(float(np.min(station_values)), 2) if station_values else 0,
            "interpolated_mean": round(float(np.mean(values)), 2) if values else 0,
            "interpolated_max": round(float(np.max(values)), 2) if values else 0,
            "interpolated_min": round(float(np.min(values)), 2) if values else 0,
        },
        "islands": {
            "lombok": {
                "stations": len([s for s in station_data if get_station_by_id(s["id"])["island"] == "Lombok"]),
                "mean": round(float(np.mean([
                    s["value"] for s in station_data
                    if get_station_by_id(s["id"])["island"] == "Lombok"
                ])), 2) if station_data else 0,
            },
            "sumbawa": {
                "stations": len([s for s in station_data if get_station_by_id(s["id"])["island"] == "Sumbawa"]),
                "mean": round(float(np.mean([
                    s["value"] for s in station_data
                    if get_station_by_id(s["id"])["island"] == "Sumbawa"
                ])), 2) if station_data else 0,
            },
        },
        "method": "IDW_interpolation",
        "scientific_basis": "Shepard (1968) - Inverse Distance Weighting interpolation",
    }


def check_regional_alerts(
    station_measurements: dict[str, dict],
    thresholds: dict | None = None,
) -> list[dict]:
    """
    Check for air quality alerts across NTB stations.

    Returns list of alerts for stations exceeding thresholds.
    """
    if thresholds is None:
        thresholds = {
            "pm10": 150,   # PP 22/2021 24h limit
            "pm25": 55,    # PP 22/2021 24h limit
            "so2": 150,    # PP 22/2021 1h limit
            "no2": 200,    # PP 22/2021 1h limit
            "co": 10000,   # PP 22/2021 8h limit
        }

    alerts = []

    for station in NTB_STATIONS:
        if station["id"] not in station_measurements:
            continue

        measurements = station_measurements[station["id"]]
        for pollutant, threshold in thresholds.items():
            value = measurements.get(pollutant)
            if value is not None and value > threshold:
                alerts.append({
                    "station_id": station["id"],
                    "station_name": station["name"],
                    "city": station["city"],
                    "island": station["island"],
                    "pollutant": pollutant,
                    "value": round(float(value), 2),
                    "threshold": threshold,
                    "exceedance_pct": round((value - threshold) / threshold * 100, 1),
                    "severity": "critical" if value > threshold * 2 else "warning",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                })

    return sorted(alerts, key=lambda x: x["exceedance_pct"], reverse=True)


def get_ntb_regional_summary(
    station_measurements: dict[str, dict],
) -> dict:
    """
    Generate regional air quality summary for NTB.

    Provides island-level and station-level summaries.
    """
    from ispu_calculator import get_overall_ispu

    station_summaries = []
    for station in NTB_STATIONS:
        if station["id"] not in station_measurements:
            continue

        measurements = station_measurements[station["id"]]
        ispu = get_overall_ispu(measurements)

        station_summaries.append({
            "station_id": station["id"],
            "station_name": station["name"],
            "city": station["city"],
            "island": station["island"],
            "type": station["type"],
            "lat": station["lat"],
            "lon": station["lon"],
            "measurements": measurements,
            "ispu": ispu,
        })

    # Island summaries
    lombok_stations = [s for s in station_summaries if s["island"] == "Lombok"]
    sumbawa_stations = [s for s in station_summaries if s["island"] == "Sumbawa"]

    def island_summary(stations):
        if not stations:
            return {"stations": 0, "mean_ispu": 0, "max_ispu": 0}
        ispu_values = [s["ispu"]["value"] for s in stations if s["ispu"]["value"]]
        return {
            "stations": len(stations),
            "mean_ispu": round(float(np.mean(ispu_values)), 1) if ispu_values else 0,
            "max_ispu": round(float(np.max(ispu_values)), 1) if ispu_values else 0,
            "critical_station": max(stations, key=lambda x: x["ispu"]["value"] or 0)["station_name"]
            if stations else None,
        }

    # Overall NTB summary
    all_ispu = [s["ispu"]["value"] for s in station_summaries if s["ispu"]["value"]]

    return {
        "region": "Nusa Tenggara Barat (NTB)",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "total_stations": len(station_summaries),
        "ntb_summary": {
            "mean_ispu": round(float(np.mean(all_ispu)), 1) if all_ispu else 0,
            "max_ispu": round(float(np.max(all_ispu)), 1) if all_ispu else 0,
            "min_ispu": round(float(np.min(all_ispu)), 1) if all_ispu else 0,
        },
        "islands": {
            "lombok": island_summary(lombok_stations),
            "sumbawa": island_summary(sumbawa_stations),
        },
        "stations": station_summaries,
        "alerts": check_regional_alerts(station_measurements),
    }
