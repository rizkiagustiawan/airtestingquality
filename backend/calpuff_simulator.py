"""
CALPUFF Long-Range Transport Simulator.
Simplified Lagrangian puff model that generates a cumulative plume GeoJSON
from all emission sources across the mining complex.
"""

import math
import random
import typing
from emission_sources import EMISSION_SOURCES


def _advect_puff(
    lat: float, lon: float,
    wind_dir_deg: float,
    wind_speed_ms: float,
    dt_s: float,
    lat_ref: float = -8.82
) -> tuple[float, float]:
    """Advect a puff position by one time step."""
    # Wind blows FROM wind_dir, so puff moves TOWARDS (wind_dir + 180)
    towards_rad = math.radians((wind_dir_deg + 180) % 360)

    dx = wind_speed_ms * math.sin(towards_rad) * dt_s  # East (m)
    dy = wind_speed_ms * math.cos(towards_rad) * dt_s  # North (m)

    lat_per_m = 1 / 111320.0
    lon_per_m = 1 / (111320.0 * math.cos(math.radians(lat_ref)))

    new_lat = lat + dy * lat_per_m
    new_lon = lon + dx * lon_per_m
    return new_lat, new_lon


def _wind_at_time(hour: int) -> tuple[float, float]:
    """Simplified time-varying wind field for Sumbawa (sea-land breeze)."""
    if 9 <= hour <= 17:
        # Daytime: onshore SSW-W
        wd = 230 + 20 * math.sin(math.pi * (hour - 9) / 8) + random.gauss(0, 10)
        ws = 3.5 + 1.5 * math.sin(math.pi * (hour - 9) / 8) + random.gauss(0, 0.5)
    elif 20 <= hour or hour <= 5:
        # Nighttime: offshore NE-E
        wd = 60 + 15 * math.sin(math.pi * (hour % 24) / 10) + random.gauss(0, 15)
        ws = 1.5 + random.gauss(0, 0.4)
    else:
        # Transition
        wd = random.uniform(0, 360)
        ws = 1.0 + random.gauss(0, 0.5)

    return wd % 360, max(0.3, ws)


def _puff_sigma(travel_time_s: float, stability: str = "C") -> float:
    """Puff growth (sigma in meters) as function of travel time."""
    growth_rates = {"A": 0.40, "B": 0.30, "C": 0.22, "D": 0.15, "E": 0.10, "F": 0.07}
    rate = growth_rates.get(stability, 0.15)
    return rate * travel_time_s


def compute_cumulative_plume(
    duration_hours: int = 12,
    dt_minutes: int = 30,
    pollutant: str = "pm10"
) -> dict:
    """
    Run a simplified CALPUFF simulation:
    1. Every dt_minutes, each source releases a puff
    2. All puffs are advected by the time-varying wind field
    3. After simulation, puff positions and sizes form the plume
    
    Returns GeoJSON for rendering the plume on Leaflet.
    """
    dt_s = dt_minutes * 60
    n_steps = int((duration_hours * 60) / dt_minutes)
    start_hour = 6  # simulation starts at 06:00 local

    # Active puff list: each puff has lat, lon, q, age_s, sigma
    puffs: list[dict] = []
    features = []

    for step in range(n_steps):
        current_hour = (start_hour + (step * dt_minutes) // 60) % 24
        wd, ws = _wind_at_time(current_hour)

        # Release new puffs from each source
        for src in EMISSION_SOURCES:
            emissions_dict = typing.cast(dict[str, float], src.get("emissions", {}))
            q = emissions_dict.get(pollutant, 0)
            if q <= 0:
                continue
            puffs.append({
                "lat": src["lat"],
                "lon": src["lon"],
                "q": q * dt_s,  # total mass released in this interval (g)
                "age_s": 0,
                "source": src["id"]
            })

        # Advect all puffs
        for puff in puffs:
            # Add some turbulent diffusion (random walk)
            wd_local = wd + random.gauss(0, 8)
            ws_local = ws * (0.9 + random.uniform(0, 0.2))
            new_lat, new_lon = _advect_puff(
                puff["lat"], puff["lon"], wd_local, ws_local, dt_s
            )
            puff["lat"] = new_lat
            puff["lon"] = new_lon
            puff["age_s"] += dt_s

    # Convert final puff positions to GeoJSON circles/polygons
    lat_per_m = 1 / 111320.0
    lon_per_m = 1 / (111320.0 * math.cos(math.radians(-8.82)))

    # Concentration bands for coloring
    for puff in puffs:
        sigma = _puff_sigma(puff["age_s"])
        sigma = max(sigma, 200)  # minimum visual size

        # Approximate ground-level concentration at puff center
        # C = Q / (2π * σxy² * σz * √(2π))  simplified
        sigma_z = sigma * 0.5
        if sigma > 0 and sigma_z > 0:
            conc = (puff["q"] * 1e6) / (2 * math.pi * sigma * sigma * sigma_z * 2.507)
        else:
            conc = 0

        if conc < 0.1:
            continue

        # Determine color based on concentration
        if conc > 100:
            color = "#DC2626"
            opacity = 0.40
        elif conc > 50:
            color = "#F59E0B"
            opacity = 0.30
        elif conc > 20:
            color = "#3B82F6"
            opacity = 0.25
        elif conc > 5:
            color = "#06B6D4"
            opacity = 0.18
        else:
            color = "#10B981"
            opacity = 0.12

        # Create an approximate hexagonal polygon representing the puff
        radius_lat = sigma * lat_per_m
        radius_lon = sigma * lon_per_m
        n_vertices = 8
        coords = []
        for k in range(n_vertices + 1):
            angle = 2 * math.pi * k / n_vertices
            plat = puff["lat"] + radius_lat * math.cos(angle)
            plon = puff["lon"] + radius_lon * math.sin(angle)
            coords.append([round(plon, 6), round(plat, 6)])

        features.append({
            "type": "Feature",
            "properties": {
                "concentration": round(conc, 2),
                "color": color,
                "opacity": opacity,
                "age_hours": round(puff["age_s"] / 3600, 1),
                "source": puff["source"],
                "sigma_m": int(sigma)
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        })

    # Sort by concentration so high-conc features render on top
    features.sort(key=lambda f: typing.cast(dict, f["properties"])["concentration"])

    # Build legend
    bands = [
        {"label": "> 100 µg/m³ (Critical)", "color": "#DC2626"},
        {"label": "50-100 µg/m³ (High)", "color": "#F59E0B"},
        {"label": "20-50 µg/m³ (Moderate)", "color": "#3B82F6"},
        {"label": "5-20 µg/m³ (Low)", "color": "#06B6D4"},
        {"label": "< 5 µg/m³ (Background)", "color": "#10B981"},
    ]

    return {
        "type": "FeatureCollection",
        "pollutant": pollutant,
        "duration_hours": duration_hours,
        "total_puffs": len(features),
        "sources_count": len(EMISSION_SOURCES),
        "bands": bands,
        "features": features
    }
