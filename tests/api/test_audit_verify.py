from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app import main
from app.database.models import AuditLog
from app.security.audit import GENESIS_HASH
from tests.api.test_ingest import DISK_ALERT

client = TestClient(main.app)


def _ingest(n: int) -> None:
    for _ in range(n):
        assert client.post("/ingest", json=DISK_ALERT).status_code == 200


def test_ingest_builds_a_valid_chain(db):
    _ingest(3)
    with db.connect() as conn:
        rows = conn.execute(select(AuditLog.seq, AuditLog.prev_hash, AuditLog.hash).order_by(AuditLog.seq)).all()
    assert [r.seq for r in rows] == [1, 2, 3]
    assert rows[0].prev_hash == GENESIS_HASH
    assert rows[1].prev_hash == rows[0].hash and rows[2].prev_hash == rows[1].hash
    assert client.get("/api/v1/audit/verify").json() == {"ok": True, "checked": 3, "broken_at_seq": None, "reason": None}


def test_empty_chain_verifies(db):
    assert client.get("/api/v1/audit/verify").json()["ok"] is True


def test_edited_row_is_detected(db):
    _ingest(3)
    with db.begin() as conn:
        conn.execute(update(AuditLog).where(AuditLog.seq == 2).values(actor="attacker"))
    body = client.get("/api/v1/audit/verify").json()
    assert body["ok"] is False and body["broken_at_seq"] == 2 and body["reason"] == "record modified"


def test_deleted_row_is_detected(db):
    _ingest(3)
    with db.begin() as conn:
        conn.execute(delete(AuditLog).where(AuditLog.seq == 2))
    body = client.get("/api/v1/audit/verify").json()
    assert body["ok"] is False and body["broken_at_seq"] == 2
