from fastapi.testclient import TestClient


def test_health_check(test_client: TestClient):
    response = test_client.get("/health")
    assert response.status_code == 200

    content = response.json()
    assert isinstance(content, dict)
    assert "status" in content
    assert "uptime" in content
    assert content["status"] == "ok"
    assert isinstance(content["uptime"], str)
