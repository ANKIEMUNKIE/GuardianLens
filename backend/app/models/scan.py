"""
GuardianLens — Scan ORM Model
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), default="other")

    # Storage paths
    original_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    heatmap_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    cert_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Scores
    trust_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # JSON fields
    breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ela_regions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    anomalies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_type_detected: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Metadata
    ai_model_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "scan_id": self.id,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "trust_score": self.trust_score,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "breakdown": self.breakdown or {},
            "ela_regions": self.ela_regions or [],
            "anomalies": self.anomalies or [],
            "ai_summary": self.ai_summary,
            "doc_type_detected": self.doc_type_detected,
            "ela_heatmap_url": f"/api/heatmap/{self.id}" if self.heatmap_path else None,
            "certificate_url": f"/api/cert/{self.id}" if self.cert_path else None,
            "ai_model_used": self.ai_model_used,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sdg_tag": "SDG 16",
        }
