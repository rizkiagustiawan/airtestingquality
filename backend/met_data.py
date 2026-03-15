"""
Meteorological Data Simulator for Sumbawa, NTB.
Generates realistic hourly wind/met data with tropical sea-land breeze patterns.
"""

import math
import random
from datetime import datetime, timedelta


def _pasquill_stability(hour: int, wind_speed: float) -> str:
    """Simplified Pasquill-Gifford stability class based on hour & wind speed."""
    is_daytime = 6 <= hour <= 18
    if is_daytime:
        if wind_speed < 2:
            return "A"  # Very unstable
        elif wind_speed < 3:
            return "B"  # Moderately unstable
        elif wind_speed < 5:
            return "C"  # Slightly unstable
        else:
            return "D"  # Neutral
    else:
        if wind_speed < 3:
            return "F"  # Stable
        elif wind_speed < 5:
            return "E"  # Slightly stable
        else:
            return "D"  # Neutral


def _mixing_height(hour: int, stability: str) -> float:
    """Estimated mixing height (m) based on time and stability."""
    base_heights = {"A": 1800, "B": 1500, "C": 1200, "D": 800, "E": 300, "F": 150}
    base = base_heights.get(stability, 500)
    # Diurnal variation – peak at 14:00
    diurnal_factor = 0.5 + 0.5 * max(0, math.sin(math.pi * (hour - 6) / 12))
    if not (6 <= hour <= 18):
        diurnal_factor = 0.3
    return round(base * diurnal_factor + random.uniform(-50, 50), 1)


def generate_met_timeseries(hours: int = 72) -> list[dict]:
    """
    Generate hourly meteorological data simulating Sumbawa tropical conditions.
    
    Wind pattern: Sea-land breeze cycle
    - Day (09-17): Onshore breeze from SSW-W (200-270°), stronger winds
    - Night (20-06): Offshore breeze from NE-E (30-90°), lighter winds
    - Transition periods with variable light winds
    """
    now = datetime.utcnow()
    data = []

    for i in range(hours):
        t = now - timedelta(hours=hours - i)
        hour = t.hour

        # --- Wind Direction (sea-land breeze cycle) ---
        if 9 <= hour <= 17:
            # Daytime: onshore (SSW to W)
            base_dir = 230 + 20 * math.sin(math.pi * (hour - 9) / 8)
            wd = base_dir + random.gauss(0, 15)
        elif 20 <= hour or hour <= 5:
            # Nighttime: offshore (NE to E)
            base_dir = 60 + 15 * math.sin(math.pi * (hour % 24) / 10)
            wd = base_dir + random.gauss(0, 20)
        else:
            # Transition: variable
            wd = random.uniform(0, 360)

        wd = wd % 360

        # --- Wind Speed ---
        if 10 <= hour <= 16:
            ws = random.gauss(4.5, 1.2)
        elif 22 <= hour or hour <= 4:
            ws = random.gauss(1.8, 0.8)
        else:
            ws = random.gauss(2.5, 1.0)
        ws = max(0.3, ws)

        # --- Temperature (tropical) ---
        temp_base = 27.0
        temp_diurnal = 4.0 * math.sin(math.pi * (hour - 6) / 12)
        if not (6 <= hour <= 18):
            temp_diurnal = -2.0
        temp = temp_base + temp_diurnal + random.gauss(0, 0.5)

        # --- Stability & Mixing Height ---
        stability = _pasquill_stability(hour, ws)
        mix_h = _mixing_height(hour, stability)

        # --- Humidity (tropical, high) ---
        rh = 75 + 10 * math.cos(math.pi * (hour - 14) / 12) + random.gauss(0, 3)
        rh = min(98, max(50, rh))

        # --- Pressure ---
        pressure = 1012 + random.gauss(0, 1.5)

        data.append({
            "timestamp": t.isoformat() + "Z",
            "hour": hour,
            "wind_speed_ms": round(ws, 2),
            "wind_direction_deg": round(wd, 1),
            "temperature_c": round(temp, 1),
            "relative_humidity_pct": round(rh, 1),
            "pressure_hpa": round(pressure, 1),
            "stability_class": stability,
            "mixing_height_m": round(mix_h, 1)
        })

    return data


def get_wind_rose_data(met_data: list[dict] | None = None) -> dict:
    """
    Compute wind rose frequency data: percentage of time wind blows
    from each 22.5° sector for each speed bin.
    """
    if met_data is None:
        met_data = generate_met_timeseries(168)  # 7 days

    n_sectors = 16
    sector_width = 360 / n_sectors
    speed_bins = [
        {"label": "0-1 m/s", "min": 0, "max": 1, "color": "#93C5FD"},
        {"label": "1-2 m/s", "min": 1, "max": 2, "color": "#60A5FA"},
        {"label": "2-3 m/s", "min": 2, "max": 3, "color": "#3B82F6"},
        {"label": "3-5 m/s", "min": 3, "max": 5, "color": "#2563EB"},
        {"label": "5-7 m/s", "min": 5, "max": 7, "color": "#1D4ED8"},
        {"label": ">7 m/s", "min": 7, "max": 999, "color": "#1E3A8A"},
    ]

    sector_labels = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

    # Initialize frequency counts
    freq: list[list[int]] = [[0] * len(speed_bins) for _ in range(n_sectors)]
    total = len(met_data)

    for rec in met_data:
        wd = rec["wind_direction_deg"]
        ws = rec["wind_speed_ms"]
        sector_idx = int(((wd + sector_width / 2) % 360) / sector_width)
        for j, sb in enumerate(speed_bins):
            if sb["min"] <= ws < sb["max"]:
                freq[sector_idx][j] += 1
                break

    # Convert to percentages
    freq_pct = []
    for i in range(n_sectors):
        sector_data = []
        for j in range(len(speed_bins)):
            sector_data.append(round(100 * freq[i][j] / max(total, 1), 2))
        freq_pct.append(sector_data)

    return {
        "sectors": sector_labels,
        "speed_bins": speed_bins,
        "frequencies": freq_pct,
        "total_observations": total,
        "calm_pct": round(100 * sum(1 for r in met_data if r["wind_speed_ms"] < 0.5) / max(total, 1), 2)
    }


def get_polar_plot_data(pollutant: str = "pm10", met_data: list[dict] | None = None) -> dict:
    """
    Simulate concentration data by wind direction and speed (polar plot).
    Higher concentrations when wind blows FROM source areas.
    """
    if met_data is None:
        met_data = generate_met_timeseries(168)

    # Simulated source direction: mining complex is broadly to the East/SE
    source_dir = 120  # Wind coming FROM this direction carries pollutant

    points = []
    for rec in met_data:
        wd = rec["wind_direction_deg"]
        ws = rec["wind_speed_ms"]

        # Higher concentration when wind comes from the source direction
        dir_diff = abs(wd - source_dir)
        if dir_diff > 180:
            dir_diff = 360 - dir_diff

        # Gaussian-like directional enhancement
        dir_factor = math.exp(-(dir_diff ** 2) / (2 * 60 ** 2))

        # Base concentration depends on wind speed (moderate wind = most transport)
        speed_factor = ws * math.exp(-ws / 5)

        base_conc = {"pm10": 45, "pm25": 15, "so2": 20, "nox": 18, "co": 800}
        base = base_conc.get(pollutant, 30)

        conc = base * (0.3 + 0.7 * dir_factor) * (0.5 + speed_factor / 3)
        conc += random.gauss(0, base * 0.05)
        conc = max(0, conc)

        points.append({
            "wind_dir": round(wd, 1),
            "wind_speed": round(ws, 2),
            "concentration": round(conc, 2)
        })

    return {
        "pollutant": pollutant,
        "unit": "µg/m³" if pollutant != "co" else "µg/m³",
        "points": points
    }


def get_timeseries_data(met_data: list[dict] | None = None) -> dict:
    """Return pollutant time series aligned with meteorological data."""
    if met_data is None:
        met_data = generate_met_timeseries(72)

    pollutants = ["pm10", "pm25", "so2", "nox", "co"]
    base_values = {"pm10": 45, "pm25": 15, "so2": 18, "nox": 12, "co": 850}

    series: dict[str, list[dict]] = {p: [] for p in pollutants}

    for rec in met_data:
        hour = rec["hour"]
        ws = rec["wind_speed_ms"]

        for p in pollutants:
            base = base_values[p]
            # Diurnal: higher during work hours (blasting, hauling)
            if 8 <= hour <= 17:
                activity_factor = 1.3 + 0.2 * math.sin(math.pi * (hour - 8) / 9)
            else:
                activity_factor = 0.6

            wind_factor = 0.8 + 0.4 * min(ws / 5, 1)
            val = base * activity_factor * wind_factor + random.gauss(0, base * 0.08)
            val = max(0, val)

            series[p].append({
                "timestamp": rec["timestamp"],
                "value": round(val, 2)
            })

    return {
        "pollutants": pollutants,
        "units": {p: "µg/m³" for p in pollutants},
        "series": series
    }
