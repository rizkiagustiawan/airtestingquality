from compliance import verify_compliance


def test_pm25_compliance_against_indonesia_and_who():
    result = verify_compliance("pm25", concentration=20.0, timeframe="24h")
    assert result["indonesia_compliant"] is True
    assert result["who_compliant"] is False
    assert result["indonesia_limit"] == 55
    assert result["who_limit"] == 15


def test_o3_fallback_timeframe_note_exists():
    result = verify_compliance("o3", concentration=80.0, timeframe="24h")
    assert "indonesia_note" in result
    assert "who_note" in result
    assert result["indonesia_compliant"] is None
    assert result["who_compliant"] is None
