from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
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
from governance import (
    append_audit_event,
    load_station_history,
    read_recent_audit_events,
    save_station_history,
)
from auth import (
    LoginRequest,
    LoginResponse,
    create_access_token,
    is_valid_user,
    require_roles,
    user_role,
)
from history_store import get_station_history, init_history_db, record_dashboard_snapshot
from qa_qc import run_qaqc
from rate_limit import SimpleRateLimitMiddleware
from settings import settings

_PREVIOUS_MEASUREMENTS_BY_STATION: dict[str, dict] = {}
_LATEST_DASHBOARD_META: dict = {}
_METRICS = {"dashboard_requests_total": 0}


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
app.add_middleware(
    SimpleRateLimitMiddleware,
    max_requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    enabled=settings.RATE_LIMIT_ENABLED,
)

frontend_dir = Path(__file__).parent.parent / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def load_runtime_history() -> None:
    try:
        _PREVIOUS_MEASUREMENTS_BY_STATION.update(load_station_history(settings.HISTORY_FILE))
    except Exception:
        pass
    try:
        init_history_db(settings.HISTORY_DB_FILE)
    except Exception:
        pass


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.post("/api/auth/token", response_model=LoginResponse)
def issue_token(payload: LoginRequest) -> LoginResponse:
    if not settings.AUTH_ENABLED:
        raise HTTPException(status_code=400, detail="Auth is disabled by configuration")
    if not is_valid_user(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = user_role(payload.username)
    token, expires_in = create_access_token(payload.username, role)
    return LoginResponse(access_token=token, expires_in_seconds=expires_in, role=role)


def _to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_stale(timestamp: str | None, stale_minutes: int) -> bool:
    dt = _to_datetime(timestamp)
    if dt is None:
        return True
    now = datetime.now(timezone.utc)
    age_seconds = (now - dt).total_seconds()
    return age_seconds > stale_minutes * 60


def _require_admin_key(request: Request) -> None:
    required = settings.ADMIN_API_KEY.strip()
    if not required:
        return
    provided = request.headers.get("x-api-key", "").strip()
    if provided != required:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")


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

    try:
        save_station_history(settings.HISTORY_FILE, _PREVIOUS_MEASUREMENTS_BY_STATION)
    except Exception:
        pass
    _METRICS["dashboard_requests_total"] += 1
    _LATEST_DASHBOARD_META.update(
        {
            "last_refresh": datetime.utcnow().isoformat() + "Z",
            "source": provenance["selected_source"],
            "fallback_used": provenance["fallback_used"],
            "count": len(dashboard_response),
            "qaqc_summary": qaqc_summary,
        }
    )
    try:
        append_audit_event(
            settings.AUDIT_LOG_FILE,
            "dashboard_data_refresh",
            {
                "source": provenance["selected_source"],
                "fallback_used": provenance["fallback_used"],
                "stations": len(dashboard_response),
                "valid_rate_pct": qaqc_summary.get("overall_valid_rate_pct"),
                "flags": qaqc_summary.get("total_flags"),
            },
        )
    except Exception:
        pass

    try:
        record_dashboard_snapshot(
            settings.HISTORY_DB_FILE,
            _LATEST_DASHBOARD_META["last_refresh"],
            provenance["selected_source"],
            provenance["fallback_used"],
            dashboard_response,
            qaqc_summary,
        )
    except Exception:
        pass

    return {
        "status": "success",
        "count": len(dashboard_response),
        "source": provenance["selected_source"],
        "fallback_used": provenance["fallback_used"],
        "qaqc_summary": qaqc_summary,
        "data": dashboard_response,
    }


@app.get("/api/data-quality")
def api_data_quality() -> dict:
    stale_minutes = settings.DATA_STALE_MINUTES
    per_station = []
    stale_count = 0
    for station_id, measurements in _PREVIOUS_MEASUREMENTS_BY_STATION.items():
        _ = measurements  # avoid lint warning for future expansion
        per_station.append(
            {
                "station_id": station_id,
                "last_updated": _LATEST_DASHBOARD_META.get("last_refresh"),
                "is_stale": _is_stale(_LATEST_DASHBOARD_META.get("last_refresh"), stale_minutes),
            }
        )
    stale_count = sum(1 for item in per_station if item["is_stale"])
    station_count = len(per_station)
    availability_pct = round(
        100.0 * (station_count - stale_count) / station_count, 2
    ) if station_count else 0.0
    return {
        "status": "success",
        "last_refresh": _LATEST_DASHBOARD_META.get("last_refresh"),
        "stale_threshold_minutes": stale_minutes,
        "stations": station_count,
        "stale_stations": stale_count,
        "availability_pct": availability_pct,
        "qaqc_summary": _LATEST_DASHBOARD_META.get("qaqc_summary", {}),
        "per_station": per_station,
    }


@app.get("/api/alerts")
def api_alerts() -> dict:
    alerts = []
    last_refresh = _LATEST_DASHBOARD_META.get("last_refresh")
    if _LATEST_DASHBOARD_META.get("fallback_used"):
        alerts.append(
            {
                "severity": "warning",
                "code": "SOURCE_FALLBACK",
                "message": "Primary source unavailable. Synthetic fallback is active.",
            }
        )
    if _is_stale(last_refresh, settings.DATA_STALE_MINUTES):
        alerts.append(
            {
                "severity": "critical",
                "code": "DATA_STALE",
                "message": f"No fresh refresh within {settings.DATA_STALE_MINUTES} minutes.",
            }
        )
    valid_rate = float(_LATEST_DASHBOARD_META.get("qaqc_summary", {}).get("overall_valid_rate_pct", 0.0))
    if last_refresh and valid_rate < settings.MIN_ACCEPTABLE_VALID_RATE_PCT:
        alerts.append(
            {
                "severity": "warning",
                "code": "LOW_VALID_RATE",
                "message": (
                    f"QA/QC valid rate {valid_rate}% below threshold "
                    f"{settings.MIN_ACCEPTABLE_VALID_RATE_PCT}%."
                ),
            }
        )
    return {"status": "success", "count": len(alerts), "alerts": alerts}


@app.get("/api/metrics")
def api_metrics() -> dict:
    return {"status": "success", "metrics": _METRICS}


@app.get("/api/audit-events")
def api_audit_events(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    _ctx: Annotated[object, Depends(require_roles("admin"))] = None,
) -> dict:
    _require_admin_key(request)
    events = read_recent_audit_events(settings.AUDIT_LOG_FILE, limit=limit)
    return {"status": "success", "count": len(events), "events": events}


@app.get("/api/history/station")
def api_station_history(
    station_id: str = Query(..., min_length=1),
    pollutant: str = Query(..., pattern="^(pm10|pm25|so2|no2|co|o3)$"),
    cleaned_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=2000),
    _ctx: Annotated[object, Depends(require_roles("admin", "viewer"))] = None,
) -> dict:
    rows = get_station_history(
        settings.HISTORY_DB_FILE,
        station_id=station_id,
        pollutant=pollutant,
        cleaned_only=cleaned_only,
        limit=limit,
    )
    return {
        "status": "success",
        "count": len(rows),
        "station_id": station_id,
        "pollutant": pollutant,
        "rows": rows,
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
