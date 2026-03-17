from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload


def test_dashboard_data_endpoint_shape():
    response = client.get("/api/dashboard-data")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["source"] in {"synthetic", "waqi"}
    assert "qaqc_summary" in payload
    assert isinstance(payload["data"], list)
    assert payload["count"] == len(payload["data"])
    if payload["data"]:
        station = payload["data"][0]
        assert "measurements_raw" in station
        assert "measurements" in station
        assert "qa_qc" in station


def test_dashboard_data_rejects_invalid_source():
    response = client.get("/api/dashboard-data?source=invalid")
    assert response.status_code == 422


def test_dashboard_data_waqi_without_token_returns_400():
    response = client.get("/api/dashboard-data?source=waqi")
    assert response.status_code == 400


def test_aermod_accepts_no2_pollutant():
    response = client.get("/api/aermod/dispersion?pollutant=no2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pollutant"] == "no2"


def test_calpuff_accepts_no2_pollutant():
    response = client.get("/api/calpuff/plume?pollutant=no2&duration_hours=3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pollutant"] == "no2"
