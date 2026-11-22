from fastapi.testclient import TestClient

from app import main
from app.api import health

client = TestClient(main.app)


def test_health_is_always_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_503_when_qdrant_is_unreachable(db):
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"postgres": "ok", "qdrant": "unavailable"}}


def test_ready_is_200_when_all_dependencies_answer(db, monkeypatch):
    async def qdrant_ok() -> str:
        return "ok"

    monkeypatch.setattr(health, "_check_qdrant", qdrant_ok)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_reports_postgres_down(monkeypatch):
    async def failing_check():
        raise ConnectionRefusedError("down")

    monkeypatch.setattr(health, "check_database", failing_check)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["postgres"] == "unavailable"
    assert "sqlite" not in response.text and "127.0.0.1" not in response.text


def test_request_id_is_generated_and_echoed():
    generated = client.get("/health").headers["X-Request-ID"]
    echoed = client.get("/health", headers={"X-Request-ID": "trace-123"}).headers["X-Request-ID"]

    assert generated
    assert echoed == "trace-123"
