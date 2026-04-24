"""
GuardianLens — Certificate & Heatmap File Serving
GET /api/cert/{scan_id} — download PDF certificate
GET /api/heatmap/{scan_id} — view ELA heatmap PNG inline
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.scan import Scan

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cert/{scan_id}", summary="Download PDF certificate")
async def download_cert(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Download the cryptographically-generated PDF authentication certificate."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.cert_path:
        raise HTTPException(status_code=404, detail="Certificate not yet generated for this scan")

    cert_path = Path(scan.cert_path)
    if not cert_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found on disk")

    return FileResponse(
        path=str(cert_path),
        media_type="application/pdf",
        filename=f"guardianlens_cert_{scan_id[:8]}.pdf",
    )


@router.get("/heatmap/{scan_id}", summary="View ELA forensic heatmap")
async def get_heatmap(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the ELA forensic heatmap PNG inline so browsers can display it directly."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.heatmap_path:
        raise HTTPException(status_code=404, detail="Heatmap not generated for this scan")

    heatmap_path = Path(scan.heatmap_path)
    if not heatmap_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap file not found on disk")

    # Use Response with explicit inline disposition — FileResponse sets 'attachment' which
    # causes browsers to download instead of displaying the image in <img> tags.
    image_bytes = heatmap_path.read_bytes()
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )
