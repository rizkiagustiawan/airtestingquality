import math
import random

from ispu_calculator import calculate_ispu
from met_data import generate_met_timeseries


def predict_aq_trends(hours: int = 24) -> dict:
    """
    Predict air quality trends for the next X hours.
    Returns a dictionary with time-series predictions for each pollutant and ISPU.
    """
    met_future = generate_met_timeseries(hours=hours, future=True)

    pollutants = ["pm10", "pm25", "so2", "no2", "co"]
    # Base values reflecting a moderate baseline in Sumbawa Barat
    base_values = {"pm10": 40, "pm25": 14, "so2": 15, "no2": 10, "co": 750}

    predictions = []

    for met in met_future:
        hour = met["hour"]
        ws = met["wind_speed_ms"]
        wd = met["wind_direction_deg"]

        # Diurnal activity factor (industrial/mining activity profile)
        # Peak during 08:00 - 17:00
        if 8 <= hour <= 17:
            activity_factor = 1.3 + 0.3 * math.sin(math.pi * (hour - 8) / 9)
        else:
            activity_factor = 0.7

        # Dispersion factor: higher wind speed = better dilution (lower conc)
        # But extremely low wind = stagnation (higher conc)
        dispersion_factor = 1.0 / (max(ws, 0.5) ** 0.5)

        # Directional factor: simulated source area at 120-150 degrees (East-SE)
        # If wind blows FROM that area, concentration increases
        source_dir = 135
        dir_diff = abs(wd - source_dir)
        if dir_diff > 180:
            dir_diff = 360 - dir_diff

        # Gaussian-like directional enhancement
        dir_factor = 1.0 + 1.2 * math.exp(-(dir_diff**2) / (2 * 45**2))

        hour_metrics = {}
        for p in pollutants:
            base = base_values[p]
            # Combine factors with a small random noise
            val = base * activity_factor * dispersion_factor * dir_factor
            val += random.gauss(0, val * 0.05)
            val = max(1.0, val)
            hour_metrics[p] = round(val, 2)

        # Calculate predicted ISPU for this hour
        # (Simplified: find highest individual ISPU)
        highest_ispu = 0
        critical_p = "pm10"
        for p, v in hour_metrics.items():
            res = calculate_ispu(p, v)
            if res["value"] > highest_ispu:
                highest_ispu = res["value"]
                critical_p = p

        predictions.append(
            {
                "timestamp": met["timestamp"],
                "hour": hour,
                "metrics": hour_metrics,
                "ispu": {
                    "value": highest_ispu,
                    "critical_parameter": critical_p,
                    "category": calculate_ispu(critical_p, hour_metrics[critical_p])["category"],
                },
                "met": {
                    "wind_speed": ws,
                    "wind_direction": wd,
                    "stability": met["stability_class"],
                },
            }
        )

    return {"hours": hours, "pollutants": pollutants, "predictions": predictions}
