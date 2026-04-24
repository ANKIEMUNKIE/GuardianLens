"""
GuardianLens — GET /api/health
Health check endpoint.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Returns system health status."""
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    gemini_available = bool(settings.GEMINI_API_KEY)

    return {
        "status": "ok",
        "version": "2.0.0",
        "gemini_available": gemini_available,
        "mock_mode": not gemini_available and settings.MOCK_GEMINI_IF_NO_KEY,
        "database": db_status,
        "sdg": "SDG 16 — Peace, Justice and Strong Institutions",
    }
