import csv
import io
import json

from report_generator import compile_historical_report, generate_summary_report


def test_generate_summary_report_json():
    stations = [
        {
            "id": "st-01",
            "location": "Loc A",
            "city": "City A",
            "ispu": {"value": 45, "category": "Baik", "critical_parameter": "pm10"},
            "measurements": {"pm10": 40, "pm25": 10},
        }
    ]
    qaqc = {"overall_valid_rate_pct": 100, "total_flags": 0}

    content, mime = generate_summary_report(stations, qaqc, format="json")
    assert mime == "application/json"

    data = json.loads(content)
    assert "report_generated_at" in data
    assert len(data["station_details"]) == 1
    assert data["station_details"][0]["location"] == "Loc A"


def test_generate_summary_report_csv():
    stations = [
        {
            "id": "st-01",
            "location": "Loc A",
            "city": "City A",
            "ispu": {"value": 45, "category": "Baik", "critical_parameter": "pm10"},
            "measurements": {"pm10": 40, "pm25": 10},
        }
    ]
    qaqc = {"overall_valid_rate_pct": 100, "total_flags": 0}

    content, mime = generate_summary_report(stations, qaqc, format="csv")
    assert mime == "text/csv"

    csv_content = content.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    assert rows[0][0] == "Station ID"
    assert rows[1][0] == "st-01"
    assert rows[1][1] == "Loc A"


def test_compile_historical_report():
    history = [
        {
            "timestamp": "2024-01-01T00:00:00Z",
            "station_id": "st-01",
            "location": "Loc A",
            "pollutant": "pm10",
            "value": 45.5,
            "ispu_value": 42,
            "qa_flag_count": 0,
        }
    ]

    content, mime = compile_historical_report(history, "st-01", "pm10")
    assert mime == "text/csv"

    csv_content = content.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    assert rows[0][0] == "Timestamp"
    assert rows[1][0] == "2024-01-01T00:00:00Z"
    assert rows[1][4] == "45.5"
