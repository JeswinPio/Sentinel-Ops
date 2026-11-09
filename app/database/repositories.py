from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Alert, AuditLog, Incident, IncidentStatus


class AuditRepository:
    """The only writer of audit_logs. Exposes append and reads; never update or delete."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def append(self, *, actor: str, action: str, incident_id: str | None = None, details: dict | None = None) -> AuditLog:
        entry = AuditLog(actor=actor, action=action, incident_id=incident_id, details=details or {})
        self.session.add(entry)
        return entry

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
