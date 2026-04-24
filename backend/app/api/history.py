"""
GuardianLens — GET /api/history
Returns paginated scan history.
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.scan import Scan

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/history", summary="Get scan history")
async def get_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=500),   # raised cap: dashboard requests 200
    verdict: str = Query(default=None, description="Filter by verdict: AUTHENTIC, SUSPICIOUS, FORGED"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated scan history.

    - **page**: page number (default 1)
    - **per_page**: results per page (max 50)
    - **verdict**: optional filter by verdict
    """
    query = select(Scan).order_by(desc(Scan.created_at))

    if verdict and verdict in ("AUTHENTIC", "SUSPICIOUS", "FORGED"):
        query = query.where(Scan.verdict == verdict)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    scans = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "scans": [
            {
                "scan_id": s.id,
                "filename": s.filename,
                "doc_type": s.doc_type,
                "trust_score": s.trust_score,
                "verdict": s.verdict,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "ela_heatmap_url": f"/api/heatmap/{s.id}" if s.heatmap_path else None,
                "certificate_url": f"/api/cert/{s.id}" if s.cert_path else None,
            }
            for s in scans
        ],
    }


@router.get("/scan/{scan_id}", summary="Get single scan result")
async def get_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full result for a specific scan ID."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return scan.to_dict()
