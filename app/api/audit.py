import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_session
from app.database.repositories import AuditRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/verify")
async def verify_audit_chain(session: AsyncSession = Depends(get_session)) -> dict:
    """Recomputes the audit hash chain. ok=false names the first broken seq (P6)."""
    try:
        return await AuditRepository(session).verify()
    except (SQLAlchemyError, OSError) as exc:
        logger.error("audit.verify_failed", extra={"error": type(exc).__name__})
        raise HTTPException(status_code=503, detail="Audit store unavailable.")
