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


def test_dashboard_data_waqi_without_token_returns_400(monkeypatch):
    monkeypatch.delenv("WAQI_TOKEN", raising=False)
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


def test_data_quality_endpoint_shape():
    client.get("/api/dashboard-data?source=synthetic")
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "availability_pct" in payload


def test_metrics_endpoint():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "metrics" in payload


def test_alerts_endpoint_shape():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "alerts" in payload


def test_history_endpoint_shape():
    dash = client.get("/api/dashboard-data?source=synthetic").json()
    station_id = dash["data"][0]["id"]
    response = client.get(f"/api/history/station?station_id={station_id}&pollutant=pm25")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["station_id"] == station_id


def test_prometheus_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "airq_api_requests_total" in response.text


def test_retention_and_backup_endpoints():
    retention = client.post("/api/history/retention/run?keep_days=1")
    assert retention.status_code == 200
    backup = client.post("/api/history/backup")
    assert backup.status_code == 200
    payload = backup.json()
    assert payload["status"] == "success"


def test_auth_posture_endpoint_shape():
    response = client.get("/api/auth/posture")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "configured_kids" in payload
