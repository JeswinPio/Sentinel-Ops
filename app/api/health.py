import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.connection import check_database

DEPENDENCY_TIMEOUT_SECONDS = 2.0

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness: the process is up. Never touches dependencies."""
    return {"status": "ok"}


async def _check_postgres() -> str:
    try:
        await check_database()
        return "ok"
    except Exception as exc:
        logger.warning("dependency.unavailable", extra={"dependency": "postgres", "error": type(exc).__name__})
        return "unavailable"


async def _check_qdrant() -> str:
    settings = get_settings()
    headers = {"api-key": settings.qdrant_api_key.get_secret_value()} if settings.qdrant_api_key else {}
    try:
        async with httpx.AsyncClient(timeout=DEPENDENCY_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{settings.qdrant_url.rstrip('/')}/readyz", headers=headers)
        return "ok" if response.status_code == 200 else "unavailable"
    except httpx.HTTPError as exc:
        logger.warning("dependency.unavailable", extra={"dependency": "qdrant", "error": type(exc).__name__})
        return "unavailable"


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness: 200 only when every dependency answers. Reports status words, never URLs or secrets."""
    checks = {"postgres": await _check_postgres(), "qdrant": await _check_qdrant()}
    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "checks": checks},
    )
