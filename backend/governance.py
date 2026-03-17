import json
from datetime import datetime
from pathlib import Path
from threading import Lock


_LOCK = Lock()


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_station_history(history_path: Path) -> dict[str, dict]:
    if not history_path.exists():
        return {}
    try:
        with history_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_station_history(history_path: Path, payload: dict[str, dict]) -> None:
    _safe_mkdir(history_path.parent)
    with _LOCK:
        with history_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)


def append_audit_event(audit_path: Path, event_type: str, details: dict) -> None:
    _safe_mkdir(audit_path.parent)
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "details": details,
    }
    with _LOCK:
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")


def read_recent_audit_events(audit_path: Path, limit: int = 50) -> list[dict]:
    if not audit_path.exists():
        return []
    lines: list[str]
    with _LOCK:
        with audit_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    events: list[dict] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                events.append(payload)
        except Exception:
            continue
    return events
