"""
GuardianLens — Scorer Unit Tests
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.scorer import compute_final_score, _score_to_verdict


class TestScorer:
    def test_high_scores_authentic(self):
        result = compute_final_score(
            ela_score=90, metadata_score=85, ocr_score=88,
            gemini_breakdown={"visual_consistency":88,"font_analysis":82,"content_coherence":90,"seal_stamp_check":85,"metadata_integrity":85},
            anomaly_list=[],
        )
        assert result["verdict"] == "AUTHENTIC"
        assert result["trust_score"] >= 75

    def test_low_scores_forged(self):
        result = compute_final_score(
            ela_score=15, metadata_score=20, ocr_score=25,
            gemini_breakdown={"visual_consistency":18,"font_analysis":22,"content_coherence":20,"seal_stamp_check":15,"metadata_integrity":20},
            anomaly_list=["clone stamp detected", "compression artifact in signature"],
        )
        assert result["verdict"] == "FORGED"
        assert result["trust_score"] < 45

    def test_mid_scores_suspicious(self):
        result = compute_final_score(
            ela_score=58, metadata_score=65, ocr_score=60,
            gemini_breakdown=None,
            anomaly_list=[],
        )
        assert result["verdict"] == "SUSPICIOUS"
        assert 45 <= result["trust_score"] < 75

    def test_score_in_range(self):
        result = compute_final_score(ela_score=50, metadata_score=50, ocr_score=50)
        assert 0 <= result["trust_score"] <= 100

    def test_result_has_required_keys(self):
        result = compute_final_score(ela_score=70, metadata_score=70, ocr_score=70)
        for k in ("trust_score", "verdict", "confidence", "breakdown"):
            assert k in result

    def test_confidence_in_range(self):
        result = compute_final_score(ela_score=70, metadata_score=70, ocr_score=70)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_verdict_thresholds(self):
        assert _score_to_verdict(100) == "AUTHENTIC"
        assert _score_to_verdict(75)  == "AUTHENTIC"
        assert _score_to_verdict(74)  == "SUSPICIOUS"
        assert _score_to_verdict(45)  == "SUSPICIOUS"
        assert _score_to_verdict(44)  == "FORGED"
        assert _score_to_verdict(0)   == "FORGED"

    def test_penalties_reduce_score(self):
        no_penalty = compute_final_score(ela_score=60, metadata_score=60, ocr_score=60, anomaly_list=[])
        with_penalty = compute_final_score(ela_score=60, metadata_score=60, ocr_score=60, anomaly_list=["clone stamp detected"])
        assert with_penalty["trust_score"] <= no_penalty["trust_score"]
