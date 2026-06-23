"""
Satellite Data Module: GEE (Sentinel-5P) + NASA POWER + Copernicus CAMS.

Integrates multiple satellite data sources for NTB air quality monitoring:

1. Google Earth Engine (Sentinel-5P):
   - NO2 tropospheric column
   - SO2 column
   - CO column
   - O3 total column

2. NASA POWER API:
   - Temperature, humidity, wind, solar radiation
   - Free, no API key required

3. Copernicus CAMS:
   - PM2.5/PM10 forecast
   - Global coverage, ~10km resolution

Scientific basis:
- Sentinel-5P: ESA satellite for atmospheric monitoring (7km resolution)
- NASA POWER: Meteorological parameters for dispersion modeling
- Copernicus CAMS: European air quality forecasting

Service account key: /home/awan/Documents/airtestingquality/gee-key.json
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

logger = logging.getLogger(__name__)

# GEE Service Account Key Path
GEE_KEY_PATH = Path(__file__).parent.parent / "gee-key.json"

# NTB bounding box
NTB_BOUNDS = {
    "lat_min": -8.9,
    "lat_max": -8.2,
    "lon_min": 115.9,
    "lon_max": 119.0,
}

# NTB station coordinates for satellite data extraction
NTB_STATION_COORDS = {
    "ntb-01": {"name": "Mataram Central", "lat": -8.5833, "lon": 116.1167},
    "ntb-02": {"name": "Lombok Airport", "lat": -8.7610, "lon": 116.2750},
    "ntb-03": {"name": "Senggigi Tourism", "lat": -8.4917, "lon": 116.0417},
    "ntb-04": {"name": "Tanjung Industrial", "lat": -8.3833, "lon": 116.1500},
    "ntb-05": {"name": "Praya Urban", "lat": -8.7050, "lon": 116.2700},
    "ntb-06": {"name": "Selong East", "lat": -8.6500, "lon": 116.5333},
    "ntb-07": {"name": "AMNT Mining", "lat": -8.8250, "lon": 116.8400},
    "ntb-08": {"name": "Sumbawa Besar", "lat": -8.4833, "lon": 117.4167},
    "ntb-09": {"name": "Dompu Central", "lat": -8.5333, "lon": 118.4667},
    "ntb-10": {"name": "Bima Regional", "lat": -8.4667, "lon": 118.7167},
    "ntb-11": {"name": "Bima Port", "lat": -8.4500, "lon": 118.7333},
    "ntb-12": {"name": "Tambora Area", "lat": -8.2500, "lon": 117.9500},
}


def _init_gee():
    """Initialize Google Earth Engine with service account credentials."""
    try:
        import ee

        if not GEE_KEY_PATH.exists():
            logger.warning("GEE key file not found: %s", GEE_KEY_PATH)
            return None

        credentials = ee.ServiceAccountCredentials(
            email="geoesg-worker@thermal-cathode-421211.iam.gserviceaccount.com",
            key_file=str(GEE_KEY_PATH),
        )
        ee.Initialize(credentials)
        return ee
    except Exception as e:
        logger.error("Failed to initialize GEE: %s", e)
        return None


def fetch_sentinel5p_data(
    lat: float = -8.58,
    lon: float = 116.12,
    days_back: int = 30,
    buffer_km: float = 10.0,
) -> dict:
    """
    Fetch Sentinel-5P satellite data for a specific location.

    Parameters:
    - lat, lon: Coordinates
    - days_back: Number of days to look back
    - buffer_km: Buffer around point for averaging

    Returns: NO2, SO2, CO, O3 concentrations from satellite
    """
    ee = _init_gee()
    if ee is None:
        return {"error": "GEE not available", "source": "fallback"}

    try:
        # Define point and buffer
        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(buffer_km * 1000)  # Convert km to meters

        # Date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        # Sentinel-5P datasets
        s5p_no2 = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
        s5p_co = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CO")
        s5p_so2 = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_SO2")
        s5p_o3 = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_O3")

        # Filter by date and region
        no2_filtered = (
            s5p_no2.filterDate(start_date, end_date)
            .filterBounds(region)
            .select("tropospheric_NO2_column_number_density")
        )

        co_filtered = (
            s5p_co.filterDate(start_date, end_date)
            .filterBounds(region)
            .select("CO_column_number_density")
        )

        so2_filtered = (
            s5p_so2.filterDate(start_date, end_date)
            .filterBounds(region)
            .select("SO2_column_number_density")
        )

        o3_filtered = (
            s5p_o3.filterDate(start_date, end_date)
            .filterBounds(region)
            .select("O3_column_number_density")
        )

        # Calculate mean values
        no2_mean = no2_filtered.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=1000
        )

        co_mean = co_filtered.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=1000
        )

        so2_mean = so2_filtered.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=1000
        )

        o3_mean = o3_filtered.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=1000
        )

        # Get results
        no2_val = no2_mean.getInfo()
        co_val = co_mean.getInfo()
        so2_val = so2_mean.getInfo()
        o3_val = o3_mean.getInfo()

        # Convert units (mol/m² -> µg/m³ approximation)
        # These are column densities, need conversion for ground-level comparison
        results = {
            "source": "sentinel5p",
            "location": {"lat": lat, "lon": lon},
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days_back,
            },
            "data": {
                "no2_column_mol_m2": _extract_value(no2_val),
                "co_column_mol_m2": _extract_value(co_val),
                "so2_column_mol_m2": _extract_value(so2_val),
                "o3_column_mol_m2": _extract_value(o3_val),
            },
            "units": {
                "no2_column_mol_m2": "mol/m²",
                "co_column_mol_m2": "mol/m²",
                "so2_column_mol_m2": "mol/m²",
                "o3_column_mol_m2": "mol/m²",
            },
            "note": "Column densities from satellite. For ground-level comparison, use with dispersion model.",
        }

        # Add estimated ground-level concentrations
        results["estimated_ground_level"] = _estimate_ground_level(
            results["data"]
        )

        return results

    except Exception as e:
        logger.error("Sentinel-5P fetch failed: %s", e)
        return {"error": str(e), "source": "fallback"}


def _extract_value(ee_result: dict) -> float | None:
    """Extract value from Earth Engine result dict."""
    if ee_result is None:
        return None
    for key, val in ee_result.items():
        if val is not None:
            return round(float(val), 6)
    return None


def _estimate_ground_level(column_data: dict) -> dict:
    """
    Estimate ground-level concentrations from column densities.

    Simplified approach using boundary layer height assumption.
    For accurate results, use with dispersion model.
    """
    # Typical boundary layer height for tropical regions (m)
    blh = 1000.0

    # Avogadro's number
    avogadro = 6.022e23

    # Molar masses (g/mol)
    molar_mass = {"no2": 46.01, "co": 28.01, "so2": 64.07, "o3": 48.0}

    estimates = {}
    for pollutant, col_mol_m2 in column_data.items():
        if col_mol_m2 is None:
            continue

        key = pollutant.replace("_column_mol_m2", "")
        if key in molar_mass:
            # Convert mol/m² to µg/m³
            # concentration = column_density * molar_mass / blh * 1e6
            conc_ugm3 = col_mol_m2 * molar_mass[key] / blh * 1e6
            estimates[f"{key}_ugm3"] = round(conc_ugm3, 2)

    return estimates


def fetch_nasa_power_data(
    lat: float = -8.58,
    lon: float = 116.12,
    start_date: str = "20260601",
    end_date: str = "20260623",
) -> dict:
    """
    Fetch meteorological data from NASA POWER API.

    Free, no API key required. Global coverage.
    Data: Temperature, humidity, wind, solar radiation.
    """
    try:
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        params = {
            "parameters": "T2M,RH2M,WS2M,WD2M,ALLSKY_SFC_SW_DWN",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": start_date,
            "end": end_date,
            "format": "JSON",
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract parameters
        props = data.get("properties", {}).get("parameter", {})

        result = {
            "source": "nasa_power",
            "location": {"lat": lat, "lon": lon},
            "period": {"start": start_date, "end": end_date},
            "data": {
                "temperature_c": _extract_daily_values(props.get("T2M", {})),
                "humidity_pct": _extract_daily_values(props.get("RH2M", {})),
                "wind_speed_ms": _extract_daily_values(props.get("WS2M", {})),
                "wind_direction_deg": _extract_daily_values(props.get("WD2M", {})),
                "solar_radiation": _extract_daily_values(
                    props.get("ALLSKY_SFC_SW_DWN", {})
                ),
            },
            "summary": {
                "temperature_mean": _calc_mean(props.get("T2M", {})),
                "humidity_mean": _calc_mean(props.get("RH2M", {})),
                "wind_speed_mean": _calc_mean(props.get("WS2M", {})),
            },
        }

        return result

    except Exception as e:
        logger.error("NASA POWER fetch failed: %s", e)
        return {"error": str(e), "source": "fallback"}


def _extract_daily_values(param_data: dict) -> dict:
    """Extract daily values from NASA POWER parameter data."""
    values = {}
    for date_key, val in param_data.items():
        if val != -999.0:  # -999 is fill value
            values[date_key] = round(float(val), 2)
    return values


def _calc_mean(param_data: dict) -> float:
    """Calculate mean of valid values."""
    vals = [v for v in param_data.values() if v != -999.0]
    return round(float(np.mean(vals)), 2) if vals else None


def fetch_ntb_satellite_summary() -> dict:
    """
    Fetch satellite data summary for all NTB stations.

    Combines:
    - Sentinel-5P for air quality (NO2, SO2, CO, O3)
    - NASA POWER for meteorological data
    """
    results = {
        "region": "Nusa Tenggara Barat (NTB)",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "sources": ["sentinel5p", "nasa_power"],
        "stations": {},
    }

    # Fetch data for key stations (not all to avoid API limits)
    key_stations = ["ntb-01", "ntb-07", "ntb-08", "ntb-10"]

    for station_id in key_stations:
        coords = NTB_STATION_COORDS.get(station_id)
        if not coords:
            continue

        # Fetch Sentinel-5P data
        s5p_data = fetch_sentinel5p_data(
            lat=coords["lat"], lon=coords["lon"], days_back=30
        )

        # Fetch NASA POWER data
        nasa_data = fetch_nasa_power_data(
            lat=coords["lat"],
            lon=coords["lon"],
            start_date="20260601",
            end_date="20260623",
        )

        results["stations"][station_id] = {
            "name": coords["name"],
            "coordinates": {"lat": coords["lat"], "lon": coords["lon"]},
            "sentinel5p": s5p_data,
            "nasa_power": nasa_data,
        }

    return results


def get_satellite_data_for_station(station_id: str) -> dict:
    """Get satellite data for a specific NTB station."""
    coords = NTB_STATION_COORDS.get(station_id)
    if not coords:
        return {"error": f"Unknown station: {station_id}"}

    # Fetch both sources
    s5p_data = fetch_sentinel5p_data(
        lat=coords["lat"], lon=coords["lon"], days_back=30
    )

    nasa_data = fetch_nasa_power_data(
        lat=coords["lat"],
        lon=coords["lon"],
        start_date="20260601",
        end_date="20260623",
    )

    return {
        "station_id": station_id,
        "station_name": coords["name"],
        "coordinates": {"lat": coords["lat"], "lon": coords["lon"]},
        "sentinel5p": s5p_data,
        "nasa_power": nasa_data,
    }
