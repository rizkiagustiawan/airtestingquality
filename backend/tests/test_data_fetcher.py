import data_fetcher


def test_auto_source_falls_back_to_synthetic_when_waqi_fails(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(data_fetcher, "fetch_waqi_indonesia_air_quality", _raise)
    stations, meta = data_fetcher.fetch_indonesia_air_quality(source="auto")

    assert meta["selected_source"] == "synthetic"
    assert meta["fallback_used"] is True
    assert isinstance(stations, list)
    assert len(stations) > 0


def test_synthetic_source_returns_synthetic_metadata():
    stations, meta = data_fetcher.fetch_indonesia_air_quality(source="synthetic")
    assert meta["selected_source"] == "synthetic"
    assert meta["fallback_used"] is False
    assert stations[0]["source"] == "synthetic"
