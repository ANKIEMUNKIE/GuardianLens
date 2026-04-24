"""
GuardianLens — POST /api/verify
Main document verification endpoint.
"""
import os
import shutil
import logging
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.scan import Scan
from app.core.pipeline import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/verify", summary="Verify document authenticity")
async def verify_document(
    request: Request,
    file: UploadFile = File(..., description="Document file (JPG, PNG, PDF, max 10MB)"),
    doc_type: str = Form(default="other", description="Optional document type hint"),
    db: AsyncSession = Depends(get_db),
):
    """
    Main GuardianLens verification endpoint.

    - **file**: Upload any document — JPEG, PNG, or PDF (max 10MB)
    - **doc_type**: Optional hint — e.g. `india_aadhaar`, `us_passport`, `medical_prescription_india`, `contract`

    Returns a full forensic analysis including trust score, ELA heatmap URL,
    breakdown scores, anomaly list, and PDF certificate URL.
    """
    # ── Validate ─────────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: JPG, PNG, PDF",
        )

    # Read and check size
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB",
        )
    if len(contents) < 512:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupted")

    # ── Save upload to disk ───────────────────────────────────
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    upload_path = settings.UPLOAD_DIR / safe_filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    with open(upload_path, "wb") as f:
        f.write(contents)

    logger.info(f"Saved upload: {upload_path} ({len(contents)} bytes)")

    # ── Run Pipeline ──────────────────────────────────────────
    try:
        result = await run_pipeline(
            file_path=str(upload_path),
            filename=file.filename,
            doc_type_hint=doc_type,
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        # Clean up upload on failure
        try:
            upload_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")

    # ── Persist to Database ───────────────────────────────────
    scan = Scan(
        id=result["scan_id"],
        filename=file.filename,
        file_hash=result["file_hash"],
        doc_type=doc_type,
        original_path=str(upload_path),
        heatmap_path=result.get("heatmap_path"),
        cert_path=result.get("cert_path"),
        trust_score=result["trust_score"],
        verdict=result["verdict"],
        confidence=result["confidence"],
        breakdown=result["breakdown"],
        ela_regions=result.get("ela_regions", []),
        anomalies=result.get("anomalies", []),
        ai_summary=result.get("ai_summary"),
        doc_type_detected=result.get("doc_type_detected"),
        ai_model_used=result.get("ai_model_used"),
        processing_time_ms=result.get("processing_time_ms"),
        created_at=datetime.utcnow(),
    )

    db.add(scan)
    await db.commit()
    logger.info(f"Scan persisted: {scan.id}")

    # ── Return Response ───────────────────────────────────────
    return JSONResponse(
        status_code=200,
        content={
            "scan_id": result["scan_id"],
            "trust_score": result["trust_score"],
            "verdict": result["verdict"],
            "confidence": result["confidence"],
            "breakdown": result["breakdown"],
            "anomalies": result.get("anomalies", []),
            "ela_heatmap_url": result.get("ela_heatmap_url"),
            "ela_regions": result.get("ela_regions", []),
            "summary": result.get("ai_summary", ""),
            "doc_type_detected": result.get("doc_type_detected"),
            "jurisdiction_context": result.get("jurisdiction_context"),
            "certificate_url": result.get("certificate_url"),
            "processing_time_ms": result.get("processing_time_ms"),
            "ai_model_used": result.get("ai_model_used"),
            "sdg_tag": "SDG 16",
            "created_at": datetime.utcnow().isoformat(),
        },
    )
