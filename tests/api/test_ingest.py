import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)

DISK_ALERT = {
    "timestamp": "2026-08-24 03:00:00",
    "service_name": "postgresql-db-01",
    "severity": "CRITICAL",
    "message": "disk_utilization_percent > 95%",
    "infrastructure_id": "postgresql-db-01"
}


@pytest.fixture(autouse=True)
def clear_logs():
    main.received_logs.clear()
    yield
    main.received_logs.clear()


def test_ingest_enriches_alert_with_playbook():
    response = client.post("/ingest", json=DISK_ALERT)

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "mitigation_found": True,
        "playbook_topic": "Database Disk Capacity Exhaustion"
    }

    logs = client.get("/logs").json()["logs"]
    assert len(logs) == 1
    assert logs[0]["service_name"] == "postgresql-db-01"
    assert logs[0]["playbook_topic"] == "Database Disk Capacity Exhaustion"


def test_ingest_without_matching_playbook():
    alert = {**DISK_ALERT, "severity": "INFO", "message": "Transaction completed successfully"}

    response = client.post("/ingest", json=alert)

    assert response.status_code == 200
    assert response.json()["mitigation_found"] is False
    assert response.json()["playbook_topic"] == "Triage Needed"


def test_ingest_rejects_malformed_payload():
    response = client.post("/ingest", json={"message": "missing fields"})

    assert response.status_code == 422


def test_root_reports_ingested_count():
    client.post("/ingest", json=DISK_ALERT)

    assert client.get("/").json()["total_ingested_logs"] == 1


def test_dashboard_and_static_ui_are_served():
    assert client.get("/dashboard").status_code == 200
    assert client.get("/ui/").status_code == 200
