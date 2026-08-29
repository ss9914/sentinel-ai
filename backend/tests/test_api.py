from app.ml.detector import AnomalyDetector


def test_registration_login_and_protection(client):
    assert client.get("/api/v1/logs").status_code == 401
    registered = client.post("/api/v1/auth/register", json={"username":"alice", "email":"alice@example.com", "password":"password-123"})
    assert registered.status_code == 201
    assert client.post("/api/v1/auth/login", json={"username":"alice", "password":"password-123"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"username":"alice", "password":"wrong-password"}).status_code == 401


def test_log_ingestion_pagination_and_summary(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.routes.enqueue_log", lambda _log_id: None)
    log = {"level":"INFO", "service":"orders", "message":"Order completed", "latency_ms": 45}
    response = client.post("/api/v1/logs", json=log, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["is_anomaly"] is False
    page = client.get("/api/v1/logs?page=1&page_size=10", headers=auth_headers).json()
    assert page["total"] == 1 and page["items"][0]["service"] == "orders"
    assert client.get("/api/v1/dashboard/summary", headers=auth_headers).json()["total_logs"] == 1


def test_detector_establishes_baseline_then_scores():
    detector = AnomalyDetector(minimum_samples=5, contamination=0.2)
    normal = {"level":"INFO", "service":"catalog", "message":"Request completed", "latency_ms":25}
    for _ in range(5): detector.analyze(normal)
    result = detector.analyze({"level":"CRITICAL", "service":"catalog", "message":"Database timeout failed exception", "latency_ms":45000, "ip_address":"10.0.0.9"})
    assert 0 <= result.score <= 1
    assert "isolation_forest" in result.details
