from ispu_calculator import calculate_ispu, get_overall_ispu


def test_calculate_ispu_pm25_returns_expected_shape():
    result = calculate_ispu("pm25", 35.0)
    assert isinstance(result["value"], int)
    assert result["category"] in {"Baik", "Sedang", "Tidak Sehat", "Sangat Tidak Sehat", "Berbahaya"}
    assert "color" in result


def test_get_overall_ispu_chooses_highest_parameter():
    metrics = {"pm25": 20.0, "pm10": 350.0, "so2": 20.0}
    result = get_overall_ispu(metrics)
    assert result["critical_parameter"] == "pm10"
    assert result["value"] >= 100
