import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import main
from app.database.connection import get_session
from app.database.models import Alert, AuditLog, Incident, IncidentStatus

client = TestClient(main.app)

DISK_ALERT = {
    "timestamp": "2026-08-24 03:00:00",
    "service_name": "postgresql-db-01",
    "severity": "CRITICAL",
    "message": "disk_utilization_percent > 95%",
    "infrastructure_id": "postgresql-db-01"
}


@pytest.fixture(autouse=True)
def clear_logs(db):
    main.received_logs.clear()
    yield
    main.received_logs.clear()


def test_ingest_enriches_alert_with_playbook():
    response = client.post("/ingest", json=DISK_ALERT)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["mitigation_found"] is True
    assert body["playbook_topic"] == "Database Disk Capacity Exhaustion"

    logs = client.get("/logs").json()["logs"]
    assert len(logs) == 1
    assert logs[0]["service_name"] == "postgresql-db-01"
    assert logs[0]["playbook_topic"] == "Database Disk Capacity Exhaustion"
    assert logs[0]["incident_id"] == body["incident_id"]


def test_ingest_persists_incident_alert_and_audit(db):
    body = client.post("/ingest", json=DISK_ALERT).json()

    with Session(db) as session:
        incident = session.get(Incident, body["incident_id"])
        assert incident is not None
        assert incident.status == IncidentStatus.RECEIVED
        assert incident.severity == "CRITICAL"
        assert incident.infrastructure_id == "postgresql-db-01"
        assert incident.alert_id == body["alert_id"]

        alert = session.get(Alert, body["alert_id"])
        assert alert.incident_id == incident.id
        assert alert.raw_payload["message"] == DISK_ALERT["message"]

        audit = session.scalars(select(AuditLog).where(AuditLog.incident_id == incident.id)).all()
        assert [entry.action for entry in audit] == ["incident.created"]
        assert audit[0].actor == "system:ingest"


def test_ingest_without_matching_playbook():
    alert = {**DISK_ALERT, "severity": "INFO", "message": "Transaction completed successfully"}

    response = client.post("/ingest", json=alert)

    assert response.status_code == 200
    assert response.json()["mitigation_found"] is False
    assert response.json()["playbook_topic"] == "Triage Needed"


def test_ingest_rejects_malformed_payload(db):
    response = client.post("/ingest", json={"message": "missing fields"})

    assert response.status_code == 422
    with Session(db) as session:
        assert session.scalars(select(Incident)).all() == []


class _BrokenSession:
    def __init__(self, error: Exception):
        self.error = error

    def add(self, _):
        pass

    async def flush(self):
        raise self.error

    async def rollback(self):
        pass


@pytest.mark.parametrize("error", [
    OperationalError("SELECT 1", {}, Exception("connection refused")),
    ConnectionRefusedError("asyncpg connect refused"),
    TimeoutError("asyncpg connect timed out"),
])
def test_ingest_returns_503_and_keeps_nothing_when_database_is_down(error):
    async def broken_session():
        yield _BrokenSession(error)

    main.app.dependency_overrides[get_session] = broken_session
    try:
        response = client.post("/ingest", json=DISK_ALERT)
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 503
    assert main.received_logs == []


def test_root_reports_ingested_count():
    client.post("/ingest", json=DISK_ALERT)

    assert client.get("/").json()["total_ingested_logs"] == 1


def test_dashboard_and_static_ui_are_served():
    assert client.get("/dashboard").status_code == 200
    assert client.get("/ui/").status_code == 200
