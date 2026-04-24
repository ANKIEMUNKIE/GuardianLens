"""
GuardianLens — Weighted Ensemble Scorer
Aggregates results from all pipeline stages into a final Trust Score.

Weights (from PRD/claude.md):
- ELA Heatmap: 35%
- Visual Consistency (from Gemini): 20%
- Font Analysis (from OCR + Gemini): 20%
- Metadata Integrity: 15%
- Content Coherence: 10%
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Stage weights (must sum to 1.0)
STAGE_WEIGHTS = {
    "ela": 0.35,
    "visual": 0.20,
    "font": 0.20,
    "metadata": 0.15,
    "content": 0.10,
}

# Penalty multipliers applied to the final score
PENALTY_CONFIG = {
    "photoshop_detected": 20,    # Raw deduction if editing software found
    "timestamp_inconsistency": 10,
    "low_ocr_confidence": 8,
    "future_date": 12,
}


def compute_final_score(
    ela_score: int,
    metadata_score: int,
    ocr_score: int,
    gemini_breakdown: Optional[dict] = None,
    anomaly_list: list[str] = None,
) -> dict:
    """
    Aggregate all stage scores into final Trust Score + verdict.

    Args:
        ela_score: 0-100, from ela.compute_ela_score()
        metadata_score: 0-100, from metadata.analyze_metadata()
        ocr_score: 0-100, from ocr.run_ocr()
        gemini_breakdown: dict with visual_consistency, font_analysis, etc. from Gemini
        anomaly_list: combined list of all anomalies for penalty calculation

    Returns:
        dict with trust_score, verdict, confidence, breakdown
    """
    anomaly_list = anomaly_list or []

    if gemini_breakdown:
        visual = gemini_breakdown.get("visual_consistency", ela_score)
        font = gemini_breakdown.get("font_analysis", ocr_score)
        content = gemini_breakdown.get("content_coherence", (ocr_score + metadata_score) // 2)
        seal = gemini_breakdown.get("seal_stamp_check", ela_score)
        meta = gemini_breakdown.get("metadata_integrity", metadata_score)
    else:
        # No Gemini — derive from existing scores
        visual = ela_score
        font = ocr_score
        content = (ocr_score + metadata_score) // 2
        seal = ela_score
        meta = metadata_score

    # Weighted ensemble
    raw_score = (
        ela_score * STAGE_WEIGHTS["ela"] +
        visual * STAGE_WEIGHTS["visual"] +
        font * STAGE_WEIGHTS["font"] +
        meta * STAGE_WEIGHTS["metadata"] +
        content * STAGE_WEIGHTS["content"]
    )

    # Apply anomaly penalties
    penalty = 0
    for anomaly in anomaly_list:
        anomaly_lower = anomaly.lower()
        for keyword, deduction in PENALTY_CONFIG.items():
            keyword_words = keyword.replace("_", " ").split()
            if all(kw in anomaly_lower for kw in keyword_words):
                penalty += deduction
                break

    final_score = max(0, min(100, int(raw_score - penalty)))
    verdict = _score_to_verdict(final_score)
    confidence = _compute_confidence(
        final_score, ela_score, visual, font, meta, content, penalty
    )

    return {
        "trust_score": final_score,
        "verdict": verdict,
        "confidence": confidence,
        "breakdown": {
            "metadata_integrity": max(0, min(100, int(meta))),
            "visual_consistency": max(0, min(100, int(visual))),
            "content_coherence": max(0, min(100, int(content))),
            "font_analysis": max(0, min(100, int(font))),
            "seal_stamp_check": max(0, min(100, int(seal))),
        },
        "penalty_applied": penalty,
    }


def _score_to_verdict(score: int) -> str:
    """Convert trust score to verdict string."""
    if score >= 75:
        return "AUTHENTIC"
    elif score >= 45:
        return "SUSPICIOUS"
    return "FORGED"


def _compute_confidence(
    final_score: int,
    ela: int,
    visual: int,
    font: int,
    meta: int,
    content: int,
    penalty: int,
) -> float:
    """
    Compute confidence based on consistency across stage scores.
    Low variance → high confidence. High variance → low confidence.
    Penalties also reduce confidence.
    """
    import statistics
    scores = [ela, visual, font, meta, content]
    try:
        stdev = statistics.stdev(scores)
    except statistics.StatisticsError:
        stdev = 0

    # Base confidence from stdev (lower stdev = more consistent = more confident)
    base_conf = max(0.45, min(0.99, 1.0 - stdev / 100))

    # Penalty reduces confidence
    conf = base_conf - (penalty / 200)
    return round(max(0.30, min(0.99, conf)), 2)
