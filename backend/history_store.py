import sqlite3
from pathlib import Path


def init_history_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS station_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                station_id TEXT NOT NULL,
                location TEXT,
                city TEXT,
                source TEXT,
                pollutant TEXT NOT NULL,
                value REAL NOT NULL,
                is_cleaned INTEGER NOT NULL,
                qa_flag_count INTEGER NOT NULL,
                ispu_value INTEGER,
                critical_parameter TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                fallback_used INTEGER NOT NULL,
                station_count INTEGER NOT NULL,
                valid_rate_pct REAL,
                total_flags INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_station_pollutant_time "
            "ON station_measurements (station_id, pollutant, timestamp)"
        )
        conn.commit()
    finally:
        conn.close()


def record_dashboard_snapshot(
    db_path: Path,
    timestamp: str,
    source: str,
    fallback_used: bool,
    stations: list[dict],
    qaqc_summary: dict,
) -> None:
    init_history_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            INSERT INTO refresh_events (timestamp, source, fallback_used, station_count, valid_rate_pct, total_flags)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                source,
                int(bool(fallback_used)),
                len(stations),
                float(qaqc_summary.get("overall_valid_rate_pct", 0.0)),
                int(qaqc_summary.get("total_flags", 0)),
            ),
        )

        for station in stations:
            station_id = str(station.get("id", ""))
            location = station.get("location")
            city = station.get("city")
            qa = station.get("qa_qc", {})
            flag_count = len(qa.get("flags", []))
            ispu = station.get("ispu", {})
            ispu_value = ispu.get("value")
            critical = ispu.get("critical_parameter")

            for pollutant, value in station.get("measurements_raw", {}).items():
                conn.execute(
                    """
                    INSERT INTO station_measurements
                    (timestamp, station_id, location, city, source, pollutant, value, is_cleaned, qa_flag_count, ispu_value, critical_parameter)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        station_id,
                        location,
                        city,
                        source,
                        pollutant,
                        float(value),
                        flag_count,
                        ispu_value if isinstance(ispu_value, int) else None,
                        critical,
                    ),
                )

            for pollutant, value in station.get("measurements", {}).items():
                conn.execute(
                    """
                    INSERT INTO station_measurements
                    (timestamp, station_id, location, city, source, pollutant, value, is_cleaned, qa_flag_count, ispu_value, critical_parameter)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        station_id,
                        location,
                        city,
                        source,
                        pollutant,
                        float(value),
                        flag_count,
                        ispu_value if isinstance(ispu_value, int) else None,
                        critical,
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def get_station_history(
    db_path: Path, station_id: str, pollutant: str, cleaned_only: bool, limit: int
) -> list[dict]:
    init_history_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT timestamp, station_id, location, city, source, pollutant, value, is_cleaned, qa_flag_count, ispu_value, critical_parameter
            FROM station_measurements
            WHERE station_id = ? AND pollutant = ? AND (? = 0 OR is_cleaned = 1)
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (station_id, pollutant, int(bool(cleaned_only)), limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
