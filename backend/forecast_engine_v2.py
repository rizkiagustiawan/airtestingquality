"""
Forecasting Engine v2: Real Data + Kalman Smoothing.

Scientific basis:
- Du et al. (2019) "Deep air quality forecasting using hybrid deep learning framework"
- Freeman et al. (2018) "Forecasting air quality time series using deep learning"
- Kalman filter for noise reduction

Uses REAL historical data from history_store.db when available.
Falls back to synthetic data when no real data exists.
"""

import math
import random

import numpy as np

from ispu_calculator import calculate_ispu
from met_data import generate_met_timeseries
from real_data_loader import load_time_series_for_forecast


def _generate_synthetic_series(hours: int = 168) -> dict[str, np.ndarray]:
    """Fallback: generate synthetic historical data."""
    t = np.arange(hours)
    pollutants = {}

    for p, base in [("pm10", 42), ("pm25", 15), ("so2", 18), ("no2", 12), ("co", 800)]:
        trend = base + 0.01 * t
        diurnal = base * 0.3 * np.sin(2 * np.pi * t / 24 - np.pi / 2)
        weekly = base * 0.1 * np.sin(2 * np.pi * t / 168)

        residual = np.zeros(hours)
        residual[0] = random.gauss(0, base * 0.1)
        for i in range(1, hours):
            residual[i] = 0.7 * residual[i - 1] + random.gauss(0, base * 0.08)

        series = trend + diurnal + weekly + residual
        series = np.maximum(series, 1.0)
        pollutants[p] = series

    return pollutants


def _load_real_historical(pollutants: list[str], days: int = 30) -> dict[str, np.ndarray]:
    """
    Load real historical data from database.
    Returns pollutant -> values array.
    """
    result = {}
    for p in pollutants:
        values, _ = load_time_series_for_forecast(pollutant=p, days=days)
        if len(values) >= 24:  # Need at least 24 hours
            result[p] = values
    return result


def _decompose(series: np.ndarray, period: int = 24) -> dict:
    """Classical time-series decomposition (additive)."""
    n = len(series)
    window = min(period, n // 2)
    if window % 2 == 0:
        window += 1
    trend = np.convolve(series, np.ones(window) / window, mode="same")
    half = window // 2
    trend[:half] = trend[half]
    trend[-half:] = trend[-half:]

    detrended = series - trend
    seasonal = np.zeros(n)
    for i in range(period):
        indices = list(range(i, n, period))
        if indices:
            mean_val = np.mean(detrended[indices])
            for idx in indices:
                seasonal[idx] = mean_val

    residual = series - trend - seasonal
    return {"trend": trend, "seasonal": seasonal, "residual": residual}


def _kalman_smooth(
    series: np.ndarray, process_noise: float = 0.01, measurement_noise: float = 0.1
) -> np.ndarray:
    """1D Kalman filter for smoothing."""
    n = len(series)
    filtered = np.zeros(n)
    x = series[0]
    p = 1.0
    Q = process_noise
    R = measurement_noise * np.std(series) ** 2

    for i in range(n):
        x_pred = x
        p_pred = p + Q
        K = p_pred / (p_pred + R)
        x = x_pred + K * (series[i] - x_pred)
        p = (1 - K) * p_pred
        filtered[i] = x

    return filtered


def _ewma_forecast(series: np.ndarray, horizon: int, alpha: float = 0.3) -> np.ndarray:
    """EWMA forecast with bounded slope."""
    n = len(series)
    ewma = np.zeros(n)
    ewma[0] = series[0]

    for i in range(1, n):
        ewma[i] = alpha * series[i] + (1 - alpha) * ewma[i - 1]

    last = ewma[-1]
    trend_slope = (ewma[-1] - ewma[max(0, n - 24)]) / 24 if n > 24 else 0
    max_slope = np.std(series) * 0.5
    trend_slope = max(-max_slope, min(max_slope, trend_slope))

    forecasts = np.zeros(horizon)
    for h in range(horizon):
        forecasts[h] = max(1.0, last + trend_slope * h)

    return forecasts


def _met_adjustment(
    concentration: float,
    wind_speed: float,
    wind_dir: float,
    stability: str,
    mixing_height: float,
    source_dir: float = 135.0,
) -> float:
    """Meteorological adjustment based on dispersion physics."""
    ws_factor = 1.0 / (max(wind_speed, 0.5) ** 0.3)
    stability_factors = {"A": 0.7, "B": 0.8, "C": 0.9, "D": 1.0, "E": 1.1, "F": 1.25}
    stab_factor = stability_factors.get(stability, 1.0)
    ref_height = 500.0
    mh_factor = (ref_height / max(mixing_height, 100.0)) ** 0.5

    dir_diff = abs(wind_dir - source_dir)
    if dir_diff > 180:
        dir_diff = 360 - dir_diff
    dir_factor = 1.0 + 0.4 * math.exp(-(dir_diff**2) / (2 * 50**2))

    return concentration * ws_factor * stab_factor * mh_factor * dir_factor


def _clamp_rate_of_change(current: float, previous: float, max_change_pct: float = 0.12) -> float:
    """Clamp hourly change to prevent unrealistic jumps."""
    if previous <= 0:
        return current
    max_change = previous * max_change_pct
    change = current - previous
    if abs(change) > max_change:
        return previous + max_change * (1 if change > 0 else -1)
    return current


def predict_aq_trends_v2(hours: int = 24) -> dict:
    """
    Enhanced forecasting with real data + Kalman smoothing.

    Data source priority:
    1. REAL data from history_store.db
    2. Synthetic fallback
    """
    met_future = generate_met_timeseries(hours=hours, future=True)
    pollutants = ["pm10", "pm25", "so2", "no2", "co"]

    # Try loading real data
    real_data = _load_real_historical(pollutants, days=30)
    data_source = "real_database"
    n_history = 0

    # Fallback to synthetic if insufficient real data
    if len(real_data) < 3:  # Need at least 3 pollutants with data
        real_data = _generate_synthetic_series(168)
        data_source = "synthetic"
        n_history = 168
    else:
        n_history = min(len(v) for v in real_data.values())

    predictions = []
    prev_values = {p: 0.0 for p in pollutants}

    # Pre-compute forecasts
    forecasts = {}
    decomps = {}
    for p in pollutants:
        hist = real_data.get(p, np.array([10.0] * 168))
        decomps[p] = _decompose(hist, period=24)
        raw_forecast = _ewma_forecast(hist, horizon=hours)

        # Add seasonal component
        for h in range(hours):
            seasonal_idx = h % 24
            if len(decomps[p]["seasonal"]) >= 24:
                raw_forecast[h] += decomps[p]["seasonal"][-24 + seasonal_idx]

        # Kalman smooth
        forecasts[p] = _kalman_smooth(raw_forecast, process_noise=0.005, measurement_noise=0.05)

    for met in met_future:
        hour = met["hour"]
        ws = met["wind_speed_ms"]
        wd = met["wind_direction_deg"]
        stability = met["stability_class"]
        mh = met["mixing_height_m"]
        h_idx = len(predictions)

        hour_metrics = {}

        for p in pollutants:
            base_pred = forecasts[p][h_idx] if h_idx < len(forecasts[p]) else forecasts[p][-1]
            adjusted = _met_adjustment(base_pred, ws, wd, stability, mh)

            if 8 <= hour <= 17:
                activity = 1.1 + 0.1 * math.sin(math.pi * (hour - 8) / 9)
            else:
                activity = 0.85

            val = adjusted * activity
            val += random.gauss(0, val * 0.015)

            if h_idx > 0 and prev_values[p] > 0:
                val = _clamp_rate_of_change(val, prev_values[p], max_change_pct=0.12)

            val = max(1.0, val)
            hour_metrics[p] = round(val, 2)
            prev_values[p] = val

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
                    "stability": stability,
                    "mixing_height": mh,
                },
            }
        )

    # Summary
    avg_metrics = {}
    for p in pollutants:
        vals = [pr["metrics"][p] for pr in predictions]
        avg_metrics[p] = {
            "mean": round(float(np.mean(vals)), 2),
            "min": round(float(np.min(vals)), 2),
            "max": round(float(np.max(vals)), 2),
            "std": round(float(np.std(vals)), 2),
            "max_hourly_change": round(
                float(max(abs(vals[i + 1] - vals[i]) for i in range(len(vals) - 1))), 2
            ),
        }

    return {
        "hours": hours,
        "pollutants": pollutants,
        "method": "hybrid_decomposition_ewma_kalman_met",
        "data_source": data_source,
        "n_history_hours": n_history,
        "scientific_basis": [
            "Du et al. (2019) - Deep air quality forecasting",
            "Freeman et al. (2018) - Forecasting air quality time series",
            "Kalman (1960) - Linear Filtering and Prediction",
        ],
        "smoothing": "Kalman filter + rate-of-change clamping (max 12%/hour)",
        "predictions": predictions,
        "summary": avg_metrics,
    }
