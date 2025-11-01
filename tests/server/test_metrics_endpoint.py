from fastapi.testclient import TestClient

from nomos.server import create_app


def test_metrics_endpoint_returns_snapshot():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v2/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "counters" in data and "latency_avg" in data
