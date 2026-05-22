import csv
import io
import json
from datetime import datetime, timezone


def generate_summary_report(
    stations_data: list[dict], qaqc_summary: dict, format: str = "json"
) -> tuple[bytes, str]:
    """
    Generate a summary report of the current air quality state.
    Returns (content, mime_type).
    """
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    report_data = {
        "report_generated_at": timestamp,
        "overall_summary": {
            "total_stations": len(stations_data),
            "qaqc_valid_rate_pct": qaqc_summary.get("overall_valid_rate_pct", 0),
            "total_flags": qaqc_summary.get("total_flags", 0),
        },
        "station_details": [],
    }

    for st in stations_data:
        ispu = st.get("ispu", {})
        report_data["station_details"].append(
            {
                "id": st.get("id"),
                "location": st.get("location"),
                "city": st.get("city"),
                "ispu_value": ispu.get("value"),
                "ispu_category": ispu.get("category"),
                "critical_parameter": ispu.get("critical_parameter"),
                "measurements": st.get("measurements", {}),
            }
        )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        # Header
        writer.writerow(
            [
                "Station ID",
                "Location",
                "City",
                "ISPU Value",
                "Category",
                "Critical Parameter",
                "PM10",
                "PM2.5",
                "SO2",
                "NO2",
                "CO",
            ]
        )
        # Rows
        for row in report_data["station_details"]:
            m = row["measurements"]
            writer.writerow(
                [
                    row["id"],
                    row["location"],
                    row["city"],
                    row["ispu_value"],
                    row["ispu_category"],
                    row["critical_parameter"],
                    m.get("pm10", ""),
                    m.get("pm25", ""),
                    m.get("so2", ""),
                    m.get("no2", ""),
                    m.get("co", ""),
                ]
            )
        return output.getvalue().encode("utf-8"), "text/csv"

    # Default JSON
    return json.dumps(report_data, indent=2).encode("utf-8"), "application/json"


def compile_historical_report(
    history_rows: list[dict], station_id: str, pollutant: str
) -> tuple[bytes, str]:
    """
    Compiles a historical trend report for a specific station and pollutant.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Timestamp",
            "Station ID",
            "Location",
            "Pollutant",
            "Value (ug/m3)",
            "ISPU Value",
            "QA Flags",
        ]
    )

    for row in history_rows:
        writer.writerow(
            [
                row["timestamp"],
                row["station_id"],
                row["location"],
                row["pollutant"],
                row["value"],
                row["ispu_value"],
                row["qa_flag_count"],
            ]
        )

    return output.getvalue().encode("utf-8"), "text/csv"
