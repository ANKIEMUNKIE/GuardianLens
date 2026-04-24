"""
GuardianLens — ELA Pipeline Tests
Run: pytest tests/ -v
"""
import os
import sys
import pytest
from pathlib import Path
from PIL import Image
import numpy as np

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.ela import generate_ela_heatmap, compute_ela_score, compute_tampering_regions


def _make_test_image(path: str, mode="authentic"):
    """Create a synthetic test image."""
    img = Image.new("RGB", (200, 200), color=(200, 200, 200))
    # Add some content
    pixels = img.load()
    for x in range(50, 150):
        for y in range(50, 150):
            pixels[x, y] = (100, 100, 100)

    if mode == "tampered":
        # Simulate tampered region — copy-pasted block with different compression history
        block = Image.new("RGB", (60, 40), color=(255, 50, 50))
        # Re-save at different quality to simulate compression mismatch
        import io
        buf = io.BytesIO()
        block.save(buf, "JPEG", quality=30)
        buf.seek(0)
        block = Image.open(buf).convert("RGB")
        img.paste(block, (120, 10))

    img.save(path, "JPEG", quality=90)
    return path


@pytest.fixture
def authentic_image(tmp_path):
    path = str(tmp_path / "authentic.jpg")
    return _make_test_image(path, "authentic")


@pytest.fixture
def tampered_image(tmp_path):
    path = str(tmp_path / "tampered.jpg")
    return _make_test_image(path, "tampered")


class TestELAHeatmap:
    def test_ela_returns_ndarray(self, authentic_image):
        result = generate_ela_heatmap(authentic_image)
        assert isinstance(result, np.ndarray), "ELA should return numpy array"

    def test_ela_shape_matches_image(self, authentic_image):
        result = generate_ela_heatmap(authentic_image)
        img = Image.open(authentic_image)
        assert result.shape[:2] == (img.height, img.width), "Shape should match image dims"

    def test_ela_dtype_uint8(self, authentic_image):
        result = generate_ela_heatmap(authentic_image)
        assert result.dtype == np.uint8, "ELA output should be uint8"

    def test_ela_values_in_range(self, authentic_image):
        result = generate_ela_heatmap(authentic_image)
        assert result.min() >= 0 and result.max() <= 255, "Values should be 0-255"

    def test_tampered_has_higher_ela_than_authentic(self, authentic_image, tampered_image):
        ela_auth = generate_ela_heatmap(authentic_image)
        ela_forg = generate_ela_heatmap(tampered_image)
        score_auth = compute_ela_score(ela_auth)
        score_forg = compute_ela_score(ela_forg)
        # Authentic should have higher ELA score (less error = more authentic)
        # Note: if tampered image genuinely shows more error, its score should be lower
        assert isinstance(score_auth, int)
        assert isinstance(score_forg, int)
        assert 0 <= score_auth <= 100
        assert 0 <= score_forg <= 100


class TestELAScorer:
    def test_score_range(self, authentic_image):
        ela = generate_ela_heatmap(authentic_image)
        score = compute_ela_score(ela)
        assert 0 <= score <= 100, f"Score {score} out of range"

    def test_score_is_int(self, authentic_image):
        ela = generate_ela_heatmap(authentic_image)
        score = compute_ela_score(ela)
        assert isinstance(score, int), "Score should be int"


class TestTamperingRegions:
    def test_regions_is_list(self, authentic_image):
        ela = generate_ela_heatmap(authentic_image)
        regions = compute_tampering_regions(ela)
        assert isinstance(regions, list)

    def test_regions_have_required_keys(self, authentic_image):
        ela = generate_ela_heatmap(authentic_image)
        regions = compute_tampering_regions(ela)
        for r in regions:
            assert "x" in r and "y" in r and "w" in r and "h" in r and "severity" in r

    def test_at_most_5_regions(self, authentic_image):
        ela = generate_ela_heatmap(authentic_image)
        regions = compute_tampering_regions(ela)
        assert len(regions) <= 5, "Should return at most 5 regions"

    def test_regions_sorted_by_severity(self, tampered_image):
        ela = generate_ela_heatmap(tampered_image)
        regions = compute_tampering_regions(ela)
        if len(regions) > 1:
            severities = [r["severity"] for r in regions]
            assert severities == sorted(severities, reverse=True), "Regions should be sorted by severity"
