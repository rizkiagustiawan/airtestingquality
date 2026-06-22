"""
Real Data Loader for ML modules.

Loads actual measurement data from:
1. history_store.db (SQLite) - historical dashboard snapshots
2. WAQI API - real-time air quality data
3. Synthetic fallback when no real data available

This module ensures ML models train on REAL data, not mock data.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from settings import settings


def load_historical_measurements(
    db_path: Path | None = None,
    station_id: str | None = None,
    pollutant: str | None = None,
    days: int = 30,
    cleaned_only: bool = True,
) -> list[dict]:
    """
    Load real historical measurements from history_store.db.

    Returns list of {timestamp, station_id, pollutant, value, ispu_value}
    """
    if db_path is None:
        db_path = settings.HISTORY_DB_FILE

    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")

        query = """
            SELECT timestamp, station_id, pollutant, value, ispu_value, is_cleaned
            FROM station_measurements
            WHERE timestamp >= ?
        """
        params = [cutoff_iso]

        if station_id:
            query += " AND station_id = ?"
            params.append(station_id)

        if pollutant:
            query += " AND pollutant = ?"
            params.append(pollutant)

        if cleaned_only:
            query += " AND is_cleaned = 1"

        query += " ORDER BY timestamp ASC"

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def load_station_pollutant_matrix(
    db_path: Path | None = None,
    station_id: str | None = None,
    days: int = 30,
) -> dict[str, list[float]]:
    """
    Load real measurements as pollutant -> values matrix.

    Returns: {"pm10": [45.2, 48.1, ...], "pm25": [12.3, 14.1, ...], ...}
    """
    rows = load_historical_measurements(
        db_path=db_path, station_id=station_id, days=days, cleaned_only=True
    )

    matrix: dict[str, list[float]] = {}
    for row in rows:
        p = row["pollutant"]
        v = row["value"]
        if p and v is not None:
            matrix.setdefault(p, []).append(float(v))

    return matrix


def load_ispu_training_data(
    db_path: Path | None = None,
    days: int = 90,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Load real measurement data for ISPU classifier training.

    Features: [pm10, pm25, so2, no2, co, hour_sin, hour_cos]
    Labels: ISPU category (0-4) based on stored ispu_value

    Returns: (X, y, feature_names)
    """
    rows = load_historical_measurements(db_path=db_path, days=days, cleaned_only=True)

    if not rows:
        return np.array([]), np.array([]), []

    # Group by timestamp + station to get complete measurement sets
    from collections import defaultdict
    import math

    groups = defaultdict(dict)
    for row in rows:
        key = (row["timestamp"], row["station_id"])
        groups[key][row["pollutant"]] = row["value"]
        if row.get("ispu_value"):
            groups[key]["_ispu"] = row["ispu_value"]
        if row.get("timestamp"):
            groups[key]["_ts"] = row["timestamp"]

    features = []
    labels = []
    feature_names = ["pm10", "pm25", "so2", "no2", "co", "hour_sin", "hour_cos"]

    for key, data in groups.items():
        # Need at least PM10 and PM2.5
        pm10 = data.get("pm10")
        pm25 = data.get("pm25")
        if pm10 is None or pm25 is None:
            continue

        so2 = data.get("so2", 0)
        no2 = data.get("no2", 0)
        co = data.get("co", 0)

        # Get ISPU category from stored value or compute
        ispu_val = data.get("_ispu")
        if ispu_val is None:
            from ispu_calculator import get_overall_ispu

            ispu_result = get_overall_ispu(
                {"pm10": pm10, "pm25": pm25, "so2": so2, "no2": no2, "co": co}
            )
            ispu_val = ispu_result.get("value", 0)

        # Map ISPU to category
        if ispu_val <= 50:
            cat_idx = 0
        elif ispu_val <= 100:
            cat_idx = 1
        elif ispu_val <= 200:
            cat_idx = 2
        elif ispu_val <= 300:
            cat_idx = 3
        else:
            cat_idx = 4

        # Temporal features from timestamp
        ts_str = data.get("_ts")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                hour = ts.hour
            except Exception:
                hour = 12
        else:
            hour = 12

        hour_sin = math.sin(2 * math.pi * hour / 24)
        hour_cos = math.cos(2 * math.pi * hour / 24)

        features.append([pm10, pm25, so2, no2, co, hour_sin, hour_cos])
        labels.append(cat_idx)

    return np.array(features), np.array(labels), feature_names


def load_time_series_for_forecast(
    db_path: Path | None = None,
    station_id: str | None = None,
    pollutant: str = "pm10",
    days: int = 30,
) -> tuple[np.ndarray, list[str]]:
    """
    Load real historical time series for forecasting.

    Returns: (values_array, timestamps_list)
    """
    rows = load_historical_measurements(
        db_path=db_path,
        station_id=station_id,
        pollutant=pollutant,
        days=days,
        cleaned_only=True,
    )

    if not rows:
        return np.array([]), []

    values = [float(r["value"]) for r in rows]
    timestamps = [r["timestamp"] for r in rows]

    return np.array(values), timestamps


def get_real_data_stats(db_path: Path | None = None) -> dict:
    """
    Get statistics about available real data in the database.
    """
    if db_path is None:
        db_path = settings.HISTORY_DB_FILE

    if not db_path.exists():
        return {
            "available": False,
            "reason": "Database file not found",
            "path": str(db_path),
        }

    conn = sqlite3.connect(str(db_path))
    try:
        # Total records
        total = conn.execute("SELECT COUNT(*) FROM station_measurements").fetchone()[0]

        # By pollutant
        by_pollutant = {}
        for row in conn.execute(
            "SELECT pollutant, COUNT(*) FROM station_measurements GROUP BY pollutant"
        ).fetchall():
            by_pollutant[row[0]] = row[1]

        # By station
        by_station = {}
        for row in conn.execute(
            "SELECT station_id, COUNT(*) FROM station_measurements GROUP BY station_id"
        ).fetchall():
            by_station[row[0]] = row[1]

        # Date range
        date_range = conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM station_measurements"
        ).fetchone()

        # Refresh events
        refresh_count = conn.execute("SELECT COUNT(*) FROM refresh_events").fetchone()[0]

        return {
            "available": total > 0,
            "total_records": total,
            "by_pollutant": by_pollutant,
            "by_station": by_station,
            "date_range": {"earliest": date_range[0], "latest": date_range[1]},
            "refresh_events": refresh_count,
            "path": str(db_path),
        }
    finally:
        conn.close()


def has_sufficient_real_data(min_records: int = 50) -> bool:
    """Check if we have enough real data for ML training."""
    stats = get_real_data_stats()
    return stats.get("available", False) and stats.get("total_records", 0) >= min_records
