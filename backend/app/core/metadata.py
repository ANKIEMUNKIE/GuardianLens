"""
GuardianLens — Metadata Forensics
Analyzes EXIF data, PDF properties, and file metadata for authenticity signals.
"""
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def analyze_metadata(file_path: str, filename: str) -> dict:
    """
    Stage 2: Metadata forensics.

    Checks:
    - EXIF data for JPEG/PNG (camera model, GPS, timestamps)
    - PDF creation/modification timestamps
    - File modification time vs claimed dates
    - Software signatures (Photoshop, GIMP, etc. = red flag)

    Returns dict with:
        score: 0-100 metadata integrity score
        anomalies: list of string findings
        metadata: raw metadata dict
    """
    ext = Path(filename).suffix.lower()
    anomalies = []
    metadata = {}

    if ext in [".jpg", ".jpeg", ".png", ".webp"]:
        score, img_anomalies, img_meta = _analyze_image_metadata(file_path)
        anomalies.extend(img_anomalies)
        metadata.update(img_meta)
    elif ext == ".pdf":
        score, pdf_anomalies, pdf_meta = _analyze_pdf_metadata(file_path)
        anomalies.extend(pdf_anomalies)
        metadata.update(pdf_meta)
    else:
        score = 70  # neutral score for unknown types

    # File system check — modification time vs now
    try:
        mtime = os.path.getmtime(file_path)
        mtime_dt = datetime.utcfromtimestamp(mtime)
        if mtime_dt > datetime.utcnow():
            anomalies.append("File modification timestamp is in the future")
            score = max(0, score - 15)
    except Exception:
        pass

    return {
        "score": max(0, min(100, score)),
        "anomalies": anomalies,
        "metadata": metadata,
    }


def _analyze_image_metadata(file_path: str) -> tuple[int, list[str], dict]:
    """Extract and analyze EXIF data from image files."""
    score = 80
    anomalies = []
    metadata = {}

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(file_path)
        exif_data = img._getexif()

        if exif_data:
            exif = {TAGS.get(k, k): v for k, v in exif_data.items() if k in TAGS}
            metadata["exif"] = {k: str(v)[:200] for k, v in exif.items()}

            # Check for editing software signatures
            software = str(exif.get("Software", "")).lower()
            suspicious_software = [
                "photoshop", "gimp", "paint.net", "affinity", "lightroom",
                "snapseed", "facetune", "fotor", "picsart"
            ]
            for sw in suspicious_software:
                if sw in software:
                    anomalies.append(f"Document processed with editing software: {exif.get('Software')}")
                    score -= 25
                    break

            # Check GPS data (suspicious for identity docs)
            if "GPSInfo" in exif:
                metadata["has_gps"] = True
                # Not necessarily an anomaly but worth noting

            # Check if DateTimeOriginal and DateTime are inconsistent
            dt_original = exif.get("DateTimeOriginal", "")
            dt_modified = exif.get("DateTime", "")
            if dt_original and dt_modified and dt_original != dt_modified:
                anomalies.append(
                    f"EXIF timestamps inconsistent: original={dt_original}, modified={dt_modified}"
                )
                score -= 10

            # Check for missing expected EXIF (identity docs from cameras usually have camera model)
            if not exif.get("Make") and not exif.get("Model"):
                metadata["no_camera_data"] = True
                # Could be a screenshot or digital-only document — slight concern
                score -= 5
        else:
            # No EXIF at all — could mean it was stripped (sometimes used to hide editing)
            metadata["no_exif"] = True
            score -= 5

    except Exception as e:
        logger.warning(f"EXIF extraction failed: {e}")
        score = 70

    return score, anomalies, metadata


def _analyze_pdf_metadata(file_path: str) -> tuple[int, list[str], dict]:
    """Extract and analyze PDF metadata."""
    score = 80
    anomalies = []
    metadata = {}

    try:
        import PyPDF2

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            info = reader.metadata

        if info:
            metadata["pdf_info"] = {
                "author": str(info.get("/Author", "")),
                "creator": str(info.get("/Creator", "")),
                "producer": str(info.get("/Producer", "")),
                "creation_date": str(info.get("/CreationDate", "")),
                "mod_date": str(info.get("/ModDate", "")),
            }

            # Check for editing tools in producer/creator
            producer = str(info.get("/Producer", "")).lower()
            creator = str(info.get("/Creator", "")).lower()
            suspicious = ["photoshop", "gimp", "inkscape", "foxit phantom", "nitro"]

            for sw in suspicious:
                if sw in producer or sw in creator:
                    anomalies.append(f"PDF created/modified with: {info.get('/Producer') or info.get('/Creator')}")
                    score -= 20
                    break

            # Check creation vs modification date
            created = str(info.get("/CreationDate", ""))
            modified = str(info.get("/ModDate", ""))
            if created and modified and created != modified:
                anomalies.append("PDF modification date differs from creation date — document was edited post-creation")
                score -= 10

        metadata["page_count"] = len(reader.pages)

    except ImportError:
        logger.warning("PyPDF2 not available — skipping PDF metadata analysis")
        score = 70
    except Exception as e:
        logger.warning(f"PDF metadata extraction failed: {e}")
        score = 65

    return score, anomalies, metadata
