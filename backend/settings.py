import os


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


settings = Settings()
