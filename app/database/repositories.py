from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Alert, AuditLog, Incident, IncidentStatus, utcnow
from app.security.audit import GENESIS_HASH, record_hash, verify_chain

AUDIT_CHAIN_LOCK_KEY = 0x5E7A11  # arbitrary constant for pg_advisory_xact_lock


class AuditRepository:
    """The only writer of audit_logs. Exposes append and reads; never update or delete."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self, *, actor: str, action: str, incident_id: str | None = None, details: dict | None = None
    ) -> AuditLog:
        """Links the entry to the previous one by hash. The caller commits."""
        if self.session.bind.dialect.name == "postgresql":
            # Serialises appenders until commit so two requests never fork the chain; seq is also UNIQUE.
            await self.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUDIT_CHAIN_LOCK_KEY})
        last = (await self.session.execute(
            select(AuditLog.seq, AuditLog.hash).where(AuditLog.seq.is_not(None)).order_by(AuditLog.seq.desc()).limit(1)
        )).first()
        seq, prev_hash = (last.seq + 1, last.hash) if last else (1, GENESIS_HASH)
        entry = AuditLog(
            seq=seq, prev_hash=prev_hash, actor=actor, action=action,
            incident_id=incident_id, details=details or {}, timestamp=utcnow(),
        )
        entry.hash = record_hash(
            seq=seq, prev_hash=prev_hash, incident_id=incident_id, actor=actor,
            action=action, details=entry.details, timestamp=entry.timestamp,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def verify(self) -> dict:
        # shortcut: loads the whole chain into memory; page through it once audit_logs passes ~100k rows.
        rows = await self.session.scalars(select(AuditLog).order_by(AuditLog.seq.asc().nulls_first()))
        return verify_chain(rows)

    async def for_incident(self, incident_id: str) -> list[AuditLog]:
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.incident_id == incident_id).order_by(AuditLog.timestamp)
        )
        return list(result.scalars())


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_from_alert(
        self, *, service: str, infrastructure_id: str, severity: str, source: str, raw_payload: dict
    ) -> tuple[Incident, Alert]:
        """Stores the raw alert and opens a RECEIVED incident for it in the current transaction."""
        incident = Incident(
            service=service,
            infrastructure_id=infrastructure_id,
            severity=severity,
            status=IncidentStatus.RECEIVED,
        )
        self.session.add(incident)
        await self.session.flush()

        alert = Alert(incident_id=incident.id, source=source, raw_payload=raw_payload)
        self.session.add(alert)
        await self.session.flush()

        incident.alert_id = alert.id
        return incident, alert

    async def get(self, incident_id: str) -> Incident | None:
        return await self.session.get(Incident, incident_id)

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(Incident)) or 0
