from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from aermod_simulator import compute_dispersion_grid
from calpuff_simulator import compute_cumulative_plume
from compliance import verify_compliance
from data_fetcher import fetch_indonesia_air_quality
from emission_sources import get_emission_sources, get_receptors, get_total_emissions
from ispu_calculator import get_overall_ispu
from met_data import (
    generate_met_timeseries,
    get_polar_plot_data,
    get_timeseries_data,
    get_wind_rose_data,
)
from settings import settings


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).parent.parent / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/api/dashboard-data")
def get_dashboard_data() -> dict:
    """Fetches telemetry, calculates ISPU, and evaluates compliance limits."""
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


@app.get("/api/emission-sources")
def api_emission_sources() -> dict:
    return {
        "sources": get_emission_sources(),
        "receptors": get_receptors(),
        "total_emissions": get_total_emissions(),
    }


@app.get("/api/met-data")
def api_met_data(hours: int = Query(72, ge=1, le=720)) -> dict:
    data = generate_met_timeseries(hours)
    return {"count": len(data), "data": data}


@app.get("/api/openair/windrose")
def api_windrose() -> dict:
    met = generate_met_timeseries(168)
    return get_wind_rose_data(met)


@app.get("/api/openair/polarplot")
def api_polarplot(pollutant: str = Query("pm10")) -> dict:
    met = generate_met_timeseries(168)
    return get_polar_plot_data(pollutant, met)


@app.get("/api/openair/timeseries")
def api_timeseries(hours: int = Query(72, ge=1, le=720)) -> dict:
    met = generate_met_timeseries(hours)
    return get_timeseries_data(met)


@app.get("/api/aermod/dispersion")
def api_aermod_dispersion(
    source_id: str = Query("smelter-stack"),
    wind_dir: float = Query(230.0, ge=0, le=360),
    wind_speed: float = Query(3.5, ge=0.1, le=30),
    stability: str = Query("C"),
) -> dict:
    return compute_dispersion_grid(
        source_id=source_id,
        wind_dir=wind_dir,
        wind_speed=wind_speed,
        stability=stability,
    )


@app.get("/api/calpuff/plume")
def api_calpuff_plume(
    duration_hours: int = Query(12, ge=1, le=48),
    pollutant: str = Query("pm10"),
) -> dict:
    try:
        return compute_cumulative_plume(duration_hours=duration_hours, pollutant=pollutant)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CALPUFF Simulation Error: {exc}") from exc


app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/")
def redirect_to_app() -> RedirectResponse:
    return RedirectResponse(url="/app/")
