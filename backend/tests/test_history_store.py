from pathlib import Path

from history_store import (
    backup_history_db,
    get_station_history,
    init_history_db,
    record_dashboard_snapshot,
    restore_history_db,
)


def test_backup_restore_roundtrip(tmp_path: Path):
    db_path = tmp_path / "history.db"
    backup_dir = tmp_path / "backups"
    init_history_db(db_path)

    record_dashboard_snapshot(
        db_path=db_path,
        timestamp="2026-01-01T00:00:00Z",
        source="synthetic",
        fallback_used=False,
        stations=[
            {
                "id": "station-1",
                "location": "Station 1",
                "city": "Mataram",
                "measurements_raw": {"pm25": 12.0},
                "measurements": {"pm25": 12.0},
                "qa_qc": {"flags": []},
                "ispu": {"value": 42, "critical_parameter": "pm25"},
            }
        ],
        qaqc_summary={"overall_valid_rate_pct": 100.0, "total_flags": 0},
    )

    backup_path = backup_history_db(db_path, backup_dir)

    record_dashboard_snapshot(
        db_path=db_path,
        timestamp="2026-01-02T00:00:00Z",
        source="synthetic",
        fallback_used=False,
        stations=[
            {
                "id": "station-1",
                "location": "Station 1",
                "city": "Mataram",
                "measurements_raw": {"pm25": 30.0},
                "measurements": {"pm25": 30.0},
                "qa_qc": {"flags": []},
                "ispu": {"value": 88, "critical_parameter": "pm25"},
            }
        ],
        qaqc_summary={"overall_valid_rate_pct": 100.0, "total_flags": 0},
    )

    restore_history_db(db_path, backup_path)
    rows = get_station_history(db_path, "station-1", "pm25", cleaned_only=True, limit=10)

    assert len(rows) == 1
    assert rows[0]["value"] == 12.0
