import os
from pathlib import Path


def _load_env_file() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    env_candidates = [repo_root / ".env", Path.cwd() / ".env"]

    for env_path in env_candidates:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
        break


_load_env_file()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://127.0.0.1:8000"]


def get_jwt_secrets() -> dict[str, str]:
    raw = os.getenv("JWT_SECRETS", "").strip()
    secrets: dict[str, str] = {}
    if raw:
        for item in raw.split(","):
            part = item.strip()
            if not part or ":" not in part:
                continue
            kid, secret = part.split(":", 1)
            kid = kid.strip()
            secret = secret.strip()
            if kid and secret:
                secrets[kid] = secret
    default_secret = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "change-me-in-production"))
    active_kid = os.getenv("JWT_ACTIVE_KID", "primary")
    if default_secret and active_kid not in secrets:
        secrets[active_kid] = default_secret
    return secrets


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
    BACKUP_DIR = RUNTIME_DIR / "backups"
    RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
    AUTH_ENABLED = _as_bool(os.getenv("AUTH_ENABLED"), default=False)
    JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "change-me-in-production"))
    JWT_ACTIVE_KID = os.getenv("JWT_ACTIVE_KID", "primary")
    JWT_SECRETS = get_jwt_secrets()
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    JWT_ISSUER = os.getenv("JWT_ISSUER", "airq-webgis")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "airq-api")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin-change-me")
    VIEWER_USERNAME = os.getenv("VIEWER_USERNAME", "viewer")
    VIEWER_PASSWORD = os.getenv("VIEWER_PASSWORD", "viewer-change-me")
    ALERT_CHANNELS = [c.strip().lower() for c in os.getenv("ALERT_CHANNELS", "").split(",") if c.strip()]
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")
    ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
    ALERT_DISPATCH_KEY = os.getenv("ALERT_DISPATCH_KEY", "")


settings = Settings()
