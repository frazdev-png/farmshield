from fastapi.testclient import TestClient


def test_root_health_endpoint(client: TestClient):
    """Verify that root /health endpoint returns 200 OK with expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "FarmShield AI" in data["service"]
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


def test_api_v1_health_endpoint(client: TestClient):
    """Verify that /api/v1/health returns 200 OK and reports database status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "FarmShield AI" in data["service"]
    assert data["database"] == "operational"
    assert "version" in data
    assert "timestamp" in data


def test_custom_error_handling_404(client: TestClient):
    """Verify that not found routes return standardized JSON error format."""
    response = client.get("/api/v1/non-existent-route")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == 404
    assert "message" in data["error"]

