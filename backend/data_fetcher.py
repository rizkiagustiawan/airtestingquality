import os
import random
from datetime import datetime

import requests


SUPPORTED_POLLUTANTS = {"pm25", "pm10", "so2", "no2", "co", "o3"}


def _normalize_pollutant(name: str) -> str:
    normalized = name.strip().lower().replace(".", "")
    aliases = {"pm2_5": "pm25", "pm2p5": "pm25"}
    return aliases.get(normalized, normalized)


def fetch_synthetic_indonesia_air_quality() -> list[dict]:
    """
    Deterministic-friendly local data generator for portfolio demos.
    """
    now_iso = datetime.utcnow().isoformat() + "Z"
    stations = [
        {
            "id": "ntb-01",
            "location": "Sumbawa Barat (AMNT Area)",
            "city": "Sumbawa Barat",
            "latitude": -8.8250,
            "longitude": 116.8400,
            "base_metrics": {"pm25": 12, "pm10": 45, "so2": 15, "no2": 10, "co": 800, "o3": 25},
        },
        {
            "id": "ntb-02",
            "location": "Mataram Central",
            "city": "Mataram",
            "latitude": -8.5833,
            "longitude": 116.1167,
            "base_metrics": {"pm25": 35, "pm10": 60, "so2": 20, "no2": 25, "co": 1200, "o3": 40},
        },
        {
            "id": "ntb-03",
            "location": "Bima Regional",
            "city": "Bima",
            "latitude": -8.4667,
            "longitude": 118.7167,
            "base_metrics": {"pm25": 22, "pm10": 50, "so2": 10, "no2": 15, "co": 950, "o3": 30},
        },
        {
            "id": "ntb-04",
            "location": "Lombok International Airport",
            "city": "Lombok Tengah",
            "latitude": -8.7610,
            "longitude": 116.2750,
            "base_metrics": {"pm25": 18, "pm10": 40, "so2": 12, "no2": 18, "co": 850, "o3": 35},
        },
    ]

    parsed_locations = []
    for st in stations:
        metrics = {}
        for param, base_val in st["base_metrics"].items():
            variation = float(base_val) * 0.15
            val = float(base_val) + random.uniform(-variation, variation)
            metrics[param] = float(f"{val:.2f}")

        parsed_locations.append(
            {
                "id": st["id"],
                "location": st["location"],
                "city": st["city"],
                "latitude": st["latitude"],
                "longitude": st["longitude"],
                "last_updated": now_iso,
                "source": "synthetic",
                "measurements": metrics,
            }
        )
    return parsed_locations


def fetch_waqi_indonesia_air_quality(
    token: str, cities: list[str], timeout_seconds: int = 8
) -> list[dict]:
    """
    Pulls current air quality snapshots from WAQI city feeds.
    """
    if not token:
        raise ValueError("WAQI token is required")

    now_iso = datetime.utcnow().isoformat() + "Z"
    stations = []
    for city in cities:
        city_key = city.strip()
        if not city_key:
            continue
        url = f"https://api.waqi.info/feed/{city_key}/"
        response = requests.get(url, params={"token": token}, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        if payload.get("status") != "ok":
            continue

        data = payload.get("data", {})
        iaqi = data.get("iaqi", {})
        geo = data.get("city", {}).get("geo", [None, None])
        station_name = data.get("city", {}).get("name", city_key)
        station_id = str(data.get("idx", city_key))

        measurements = {}
        for key, value in iaqi.items():
            pollutant = _normalize_pollutant(key)
            if pollutant not in SUPPORTED_POLLUTANTS:
                continue
            reading = value.get("v") if isinstance(value, dict) else None
            if isinstance(reading, (int, float)):
                measurements[pollutant] = float(reading)

        if not measurements:
            continue

        stations.append(
            {
                "id": f"waqi-{station_id}",
                "location": station_name,
                "city": city_key,
                "latitude": geo[0],
                "longitude": geo[1],
                "last_updated": now_iso,
                "source": "waqi",
                "measurements": measurements,
            }
        )
    return stations


def fetch_indonesia_air_quality(source: str = "auto") -> tuple[list[dict], dict]:
    """
    Returns station data and provenance metadata.
    source: auto | synthetic | waqi
    """
    selected = source.strip().lower()
    if selected not in {"auto", "synthetic", "waqi"}:
        raise ValueError("Unsupported source. Use auto, synthetic, or waqi.")

    waqi_token = os.getenv("WAQI_TOKEN", "").strip()
    waqi_cities = os.getenv("WAQI_CITIES", "jakarta,bandung,surabaya,mataram").split(",")
    timeout_seconds = int(os.getenv("DATA_TIMEOUT_SECONDS", "8"))

    if selected == "synthetic":
        return fetch_synthetic_indonesia_air_quality(), {"selected_source": "synthetic", "fallback_used": False}

    if selected == "waqi":
        data = fetch_waqi_indonesia_air_quality(
            token=waqi_token, cities=waqi_cities, timeout_seconds=timeout_seconds
        )
        return data, {"selected_source": "waqi", "fallback_used": False}

    try:
        data = fetch_waqi_indonesia_air_quality(
            token=waqi_token, cities=waqi_cities, timeout_seconds=timeout_seconds
        )
        if data:
            return data, {"selected_source": "waqi", "fallback_used": False}
    except Exception:
        pass

    return fetch_synthetic_indonesia_air_quality(), {"selected_source": "synthetic", "fallback_used": True}
