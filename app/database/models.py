"""PostgreSQL tables from spec §27. Portable column types so tests can run on SQLite."""

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    RECEIVED = "RECEIVED"
    TRIAGING = "TRIAGING"
    PLAYBOOK_SEARCH = "PLAYBOOK_SEARCH"
    ANALYZING = "ANALYZING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"


class IncidentCategory(StrEnum):
    DATABASE = "DATABASE"
    CPU = "CPU"
    MEMORY = "MEMORY"
    DISK = "DISK"
    NETWORK = "NETWORK"
    SERVICE = "SERVICE"
    DEPLOYMENT = "DEPLOYMENT"
    SECURITY = "SECURITY"
    UNKNOWN = "UNKNOWN"


TZDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    alert_id: Mapped[str | None] = mapped_column(String(36))
    service: Mapped[str] = mapped_column(String(255))
    infrastructure_id: Mapped[str] = mapped_column(String(255), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32), default=IncidentCategory.UNKNOWN)
    status: Mapped[str] = mapped_column(String(32), default=IncidentStatus.RECEIVED, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    resolution_summary: Mapped[str | None] = mapped_column(Text)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), index=True)
    source: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    requested_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(TZDateTime)
    reason: Mapped[str | None] = mapped_column(Text)


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(128))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    status: Mapped[str] = mapped_column(String(32))
    output: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)


class PlaybookVersion(Base):
    __tablename__ = "playbook_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    playbook_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class AuditLog(Base):
    """Append-only from the application's perspective: only AuditRepository.append writes here."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), index=True)
    actor: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(128))
    # "metadata" is reserved on declarative classes, so the attribute is named details.
    details: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    # Hash chain (app/security/audit.py). Nullable only so the migration works on tables with older rows.
    seq: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    hash: Mapped[str | None] = mapped_column(String(64))


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(64))
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    latency: Mapped[float | None] = mapped_column(Float)
    token_usage: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
