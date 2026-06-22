from forecast_engine import predict_aq_trends


def test_predict_aq_trends_returns_expected_structure():
    hours = 12
    result = predict_aq_trends(hours=hours)

    assert result["hours"] == hours
    assert "pollutants" in result
    assert len(result["predictions"]) == hours

    # Check first prediction point
    first = result["predictions"][0]
    assert "timestamp" in first
    assert "metrics" in first
    assert "ispu" in first
    assert "met" in first

    # Check ISPU fields
    assert "value" in first["ispu"]
    assert "category" in first["ispu"]
    assert "critical_parameter" in first["ispu"]

    # Check met fields
    assert "wind_speed" in first["met"]
    assert "wind_direction" in first["met"]


def test_predict_aq_trends_values_within_bounds():
    result = predict_aq_trends(hours=24)
    for p in result["predictions"]:
        # ISPU should be non-negative
        assert p["ispu"]["value"] >= 0
        # Concentration should be non-negative
        for val in p["metrics"].values():
            assert val >= 0
