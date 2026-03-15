from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

# Import local modules
from data_fetcher import fetch_indonesia_air_quality
from ispu_calculator import get_overall_ispu
from compliance import verify_compliance
from emission_sources import get_emission_sources, get_receptors, get_total_emissions
from met_data import generate_met_timeseries, get_wind_rose_data, get_polar_plot_data, get_timeseries_data
from aermod_simulator import compute_dispersion_grid
from calpuff_simulator import compute_cumulative_plume

app = FastAPI(title="Air Quality Web GIS", version="2.0.0")

# Setup CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).parent.parent / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# EXISTING ENDPOINTS (Monitoring / ISPU)
# ──────────────────────────────────────────────

@app.get("/api/dashboard-data")
def get_dashboard_data() -> dict:
    """Fetches raw data, calculates ISPU, and runs compliance checks."""
    stations_data = fetch_indonesia_air_quality()
    dashboard_response = []

    for station in stations_data:
        metrics = station.get("measurements", {})
        overall_ispu = get_overall_ispu(metrics)
        compliance_results = []
        for param, val in metrics.items():
            comp = verify_compliance(parameter=param, concentration=val)
            if comp.get("status") != "unknown":
                compliance_results.append(comp)

        station["ispu"] = overall_ispu
        station["compliance"] = compliance_results
        dashboard_response.append(station)

    return {"status": "success", "count": len(dashboard_response), "data": dashboard_response}


# ──────────────────────────────────────────────
# EMISSION SOURCES
# ──────────────────────────────────────────────

@app.get("/api/emission-sources")
def api_emission_sources() -> dict:
    """Return all emission sources and receptor locations."""
    return {
        "sources": get_emission_sources(),
        "receptors": get_receptors(),
        "total_emissions": get_total_emissions()
    }


# ──────────────────────────────────────────────
# METEOROLOGICAL DATA
# ──────────────────────────────────────────────

@app.get("/api/met-data")
def api_met_data(hours: int = Query(72, ge=1, le=720)) -> dict:
    """Return hourly meteorological time series."""
    data = generate_met_timeseries(hours)
    return {"count": len(data), "data": data}


# ──────────────────────────────────────────────
# OPENAIR MODULE ENDPOINTS
# ──────────────────────────────────────────────

@app.get("/api/openair/windrose")
def api_windrose() -> dict:
    """Wind rose frequency data by direction sector and speed bin."""
    met = generate_met_timeseries(168)  # 7 days
    return get_wind_rose_data(met)


@app.get("/api/openair/polarplot")
def api_polarplot(pollutant: str = Query("pm10")) -> dict:
    """Polar plot concentration data by wind direction and speed."""
    met = generate_met_timeseries(168)
    return get_polar_plot_data(pollutant, met)


@app.get("/api/openair/timeseries")
def api_timeseries(hours: int = Query(72, ge=1, le=720)) -> dict:
    """Pollutant time series data."""
    met = generate_met_timeseries(hours)
    return get_timeseries_data(met)


# ──────────────────────────────────────────────
# AERMOD MODULE ENDPOINTS
# ──────────────────────────────────────────────

@app.get("/api/aermod/dispersion")
def api_aermod_dispersion(
    source_id: str = Query("smelter-stack"),
    wind_dir: float = Query(230.0, ge=0, le=360),
    wind_speed: float = Query(3.5, ge=0.1, le=30),
    stability: str = Query("C")
) -> dict:
    """
    AERMOD-style Gaussian plume dispersion contours (GeoJSON).
    Returns concentration grid as polygon features.
    """
    return compute_dispersion_grid(
        source_id=source_id,
        wind_dir=wind_dir,
        wind_speed=wind_speed,
        stability=stability
    )


# ──────────────────────────────────────────────
# CALPUFF MODULE ENDPOINTS
# ──────────────────────────────────────────────

@app.get("/api/calpuff/plume")
def api_calpuff_plume(
    duration_hours: int = Query(12, ge=1, le=48),
    pollutant: str = Query("pm10")
) -> dict:
    """
    CALPUFF-style cumulative plume transport from all sources (GeoJSON).
    Simulates multi-hour puff advection through time-varying wind field.
    """
    return compute_cumulative_plume(
        duration_hours=duration_hours,
        pollutant=pollutant
    )


# ──────────────────────────────────────────────
# STATIC FILES & REDIRECT
# ──────────────────────────────────────────────

app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

@app.get("/")
def redirect_to_app() -> RedirectResponse:
    return RedirectResponse(url="/app/")
