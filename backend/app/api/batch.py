"""
GuardianLens — POST /api/batch
Batch document verification: upload up to 20 files, get all results.
Runs pipeline concurrently (bounded to 4 parallel) for speed.
"""
import asyncio
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
MAX_BATCH_SIZE = 20
BATCH_CONCURRENCY = 4  # max parallel pipelines


@router.post("/batch", summary="Batch verify multiple documents")
async def batch_verify(
    request: Request,
    files: list[UploadFile] = File(..., description="Up to 20 document files"),
    doc_type: str = Form(default="other", description="Document type hint (applied to all)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch verification endpoint.

    - **files**: list of document files (max 20, each max 10MB)
    - **doc_type**: optional type hint applied to all files

    Returns array of results — same schema as /api/verify per item.
    Failed files are returned with `error` field instead of crashing the batch.
    """
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum batch size is {MAX_BATCH_SIZE}.",
        )

    # ── Save all uploads to disk first ───────────────────────
    upload_tasks = []
    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            upload_tasks.append({"error": f"Unsupported type '{ext}': {upload.filename}", "filename": upload.filename})
            continue

        contents = await upload.read()
        if len(contents) > MAX_BYTES:
            upload_tasks.append({"error": f"File too large (max {settings.MAX_FILE_SIZE_MB}MB): {upload.filename}", "filename": upload.filename})
            continue
        if len(contents) < 512:
            upload_tasks.append({"error": f"File empty or corrupted: {upload.filename}", "filename": upload.filename})
            continue

        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}{ext}"
        upload_path = settings.UPLOAD_DIR / safe_filename
        upload_path.parent.mkdir(parents=True, exist_ok=True)

        with open(upload_path, "wb") as f:
            f.write(contents)

        upload_tasks.append({
            "file_path": str(upload_path),
            "filename": upload.filename,
        })

    # ── Run pipelines concurrently (bounded semaphore) ────────
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def run_single(task: dict) -> dict:
        if "error" in task:
            return {"filename": task["filename"], "error": task["error"], "status": "failed"}

        async with semaphore:
            try:
                result = await run_pipeline(
                    file_path=task["file_path"],
                    filename=task["filename"],
                    doc_type_hint=doc_type,
                )
                # Persist to DB
                scan = Scan(
                    id=result["scan_id"],
                    filename=task["filename"],
                    file_hash=result["file_hash"],
                    doc_type=doc_type,
                    original_path=task["file_path"],
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

                return {
                    "filename": task["filename"],
                    "scan_id": result["scan_id"],
                    "trust_score": result["trust_score"],
                    "verdict": result["verdict"],
                    "confidence": result["confidence"],
                    "anomalies": result.get("anomalies", []),
                    "ela_heatmap_url": result.get("ela_heatmap_url"),
                    "certificate_url": result.get("certificate_url"),
                    "processing_time_ms": result.get("processing_time_ms"),
                    "status": "success",
                }
            except Exception as e:
                logger.error(f"Batch pipeline failed for {task['filename']}: {e}")
                return {"filename": task["filename"], "error": str(e), "status": "failed"}

    results = await asyncio.gather(*[run_single(t) for t in upload_tasks])
    await db.commit()

    # ── Summary stats ──────────────────────────────────────────
    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "failed"]

    summary = {
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "authentic": sum(1 for r in successful if r.get("verdict") == "AUTHENTIC"),
        "suspicious": sum(1 for r in successful if r.get("verdict") == "SUSPICIOUS"),
        "forged": sum(1 for r in successful if r.get("verdict") == "FORGED"),
        "avg_trust_score": (
            round(sum(r["trust_score"] for r in successful) / len(successful), 1)
            if successful else 0
        ),
    }

    return JSONResponse(
        status_code=200,
        content={"summary": summary, "results": list(results)},
    )
