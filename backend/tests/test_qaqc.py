from qa_qc import run_qaqc_on_station


def test_qaqc_marks_out_of_range_and_missing():
    station = {
        "id": "test-1",
        "measurements": {
            "pm25": -1.0,
            "pm10": 40.0,
            "so2": 10.0,
            "no2": 20.0,
            "co": 500.0,
        },
    }
    result = run_qaqc_on_station(station)
    assert "pm25" not in result["measurements"]
    assert result["qa_qc"]["valid_count"] == 4
    codes = {flag["code"] for flag in result["qa_qc"]["flags"]}
    assert "out_of_range" in codes
    assert "missing" in codes


def test_qaqc_keeps_numeric_values():
    station = {
        "id": "test-2",
        "measurements": {"pm25": 10, "pm10": 20, "so2": 15, "no2": 12, "co": 700, "o3": 30},
    }
    result = run_qaqc_on_station(station)
    assert result["qa_qc"]["valid_count"] == 6
    assert result["qa_qc"]["flags"] == []
