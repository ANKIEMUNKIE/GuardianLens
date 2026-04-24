"""
GuardianLens — Pydantic Request/Response Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VerifyRequest(BaseModel):
    doc_type: str = Field(default="other", description="Document type hint")


class BreakdownSchema(BaseModel):
    metadata_integrity: int = Field(ge=0, le=100)
    visual_consistency: int = Field(ge=0, le=100)
    content_coherence: int = Field(ge=0, le=100)
    font_analysis: int = Field(ge=0, le=100)
    seal_stamp_check: int = Field(ge=0, le=100)


class ELARegion(BaseModel):
    x: int
    y: int
    w: int
    h: int
    severity: float
    label: str = "Suspicious region"


class VerifyResponse(BaseModel):
    scan_id: str
    trust_score: int = Field(ge=0, le=100)
    verdict: str  # AUTHENTIC | SUSPICIOUS | FORGED
    confidence: float = Field(ge=0.0, le=1.0)
    breakdown: BreakdownSchema
    anomalies: list[str] = []
    ela_heatmap_url: Optional[str] = None
    ela_regions: list[ELARegion] = []
    summary: str
    doc_type_detected: Optional[str] = None
    jurisdiction_context: Optional[str] = None
    certificate_url: Optional[str] = None
    processing_time_ms: int
    ai_model_used: str = "gemini-pro-vision"
    sdg_tag: str = "SDG 16"
    created_at: Optional[str] = None


class ScanHistoryItem(BaseModel):
    scan_id: str
    filename: str
    doc_type: str
    trust_score: Optional[int]
    verdict: Optional[str]
    created_at: Optional[str]
    ela_heatmap_url: Optional[str]
    certificate_url: Optional[str]


class HistoryResponse(BaseModel):
    total: int
    page: int
    per_page: int
    scans: list[ScanHistoryItem]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
    gemini_available: bool
    database: str = "connected"
