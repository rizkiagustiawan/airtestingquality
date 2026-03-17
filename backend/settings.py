import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://127.0.0.1:8000"]


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Air Quality Web GIS")
    APP_VERSION = os.getenv("APP_VERSION", "2.1.0")
    CORS_ORIGINS = get_cors_origins()
    CORS_ALLOW_CREDENTIALS = _as_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), default=False)
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    DATA_SOURCE = os.getenv("DATA_SOURCE", "auto")
    RATE_LIMIT_ENABLED = _as_bool(os.getenv("RATE_LIMIT_ENABLED"), default=True)
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
    DATA_STALE_MINUTES = int(os.getenv("DATA_STALE_MINUTES", "30"))
    MIN_ACCEPTABLE_VALID_RATE_PCT = float(os.getenv("MIN_ACCEPTABLE_VALID_RATE_PCT", "85"))
    RUNTIME_DIR = Path(os.getenv("RUNTIME_DIR", str(Path(__file__).resolve().parent / "runtime")))
    HISTORY_FILE = RUNTIME_DIR / "station_history.json"
    AUDIT_LOG_FILE = RUNTIME_DIR / "audit_log.jsonl"
    HISTORY_DB_FILE = RUNTIME_DIR / "history.db"
    AUTH_ENABLED = _as_bool(os.getenv("AUTH_ENABLED"), default=False)
    JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "change-me-in-production"))
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin-change-me")
    VIEWER_USERNAME = os.getenv("VIEWER_USERNAME", "viewer")
    VIEWER_PASSWORD = os.getenv("VIEWER_PASSWORD", "viewer-change-me")


settings = Settings()
