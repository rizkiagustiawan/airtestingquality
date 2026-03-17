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
from qa_qc import run_qaqc
from settings import settings

_PREVIOUS_MEASUREMENTS_BY_STATION: dict[str, dict] = {}


def _compliance_timeframe_for(parameter: str) -> str:
    normalized = parameter.lower().replace(".", "")
    return {
        "pm25": "24h",
        "pm10": "24h",
        "so2": "1h",
        "no2": "1h",
        "co": "8h",
        "o3": "8h",
    }.get(normalized, "24h")


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
def get_dashboard_data(
    source: str = Query(settings.DATA_SOURCE, pattern="^(auto|synthetic|waqi)$")
) -> dict:
    """Fetches telemetry, calculates ISPU, and evaluates compliance limits."""
    try:
        stations_data, provenance = fetch_indonesia_air_quality(source=source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    stations_data, qaqc_summary = run_qaqc(
        stations_data, previous_by_station=_PREVIOUS_MEASUREMENTS_BY_STATION
    )
    dashboard_response = []

    for station in stations_data:
        station_id = str(station.get("id", ""))
        metrics = station.get("measurements", {})
        overall_ispu = get_overall_ispu(metrics)
        compliance_results = []
        for param, val in metrics.items():
            timeframe = _compliance_timeframe_for(param)
            comp = verify_compliance(parameter=param, concentration=val, timeframe=timeframe)
            if comp.get("status") != "unknown":
                compliance_results.append(comp)

        station["ispu"] = overall_ispu
        station["compliance"] = compliance_results
        dashboard_response.append(station)
        _PREVIOUS_MEASUREMENTS_BY_STATION[station_id] = dict(metrics)

    return {
        "status": "success",
        "count": len(dashboard_response),
        "source": provenance["selected_source"],
        "fallback_used": provenance["fallback_used"],
        "qaqc_summary": qaqc_summary,
        "data": dashboard_response,
    }


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
    pollutant: str = Query("pm10", pattern="^(pm10|pm25|so2|no2|co)$"),
    wind_dir: float = Query(230.0, ge=0, le=360),
    wind_speed: float = Query(3.5, ge=0.1, le=30),
    stability: str = Query("C"),
) -> dict:
    return compute_dispersion_grid(
        source_id=source_id,
        pollutant=pollutant,
        wind_dir=wind_dir,
        wind_speed=wind_speed,
        stability=stability,
    )


@app.get("/api/calpuff/plume")
def api_calpuff_plume(
    duration_hours: int = Query(12, ge=1, le=48),
    pollutant: str = Query("pm10", pattern="^(pm10|pm25|so2|no2|co)$"),
) -> dict:
    try:
        return compute_cumulative_plume(duration_hours=duration_hours, pollutant=pollutant)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CALPUFF Simulation Error: {exc}") from exc


app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/")
def redirect_to_app() -> RedirectResponse:
    return RedirectResponse(url="/app/")
