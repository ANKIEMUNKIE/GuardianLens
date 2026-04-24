"""
GuardianLens — OCR + Font Analysis
Tesseract-based OCR for text extraction and font consistency checks.
Gracefully degrades if Tesseract is not installed.
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def run_ocr(image_path: str) -> dict:
    """
    Stage 3: Run Tesseract OCR on the document image.

    Returns:
        text: extracted raw text
        words: list of word-level data (bbox, confidence)
        score: 0-100 font/content consistency score
        anomalies: list of findings
    """
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)

        # Get raw text
        text = pytesseract.image_to_string(img, lang="eng")

        # Get word-level data including confidence
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        words = []
        low_conf_count = 0

        for i, conf in enumerate(data["conf"]):
            if conf == -1:
                continue
            try:
                conf_val = int(conf)
            except (ValueError, TypeError):
                continue

            if conf_val > 0:
                words.append({
                    "text": data["text"][i],
                    "conf": conf_val,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                })
                if conf_val < 50:
                    low_conf_count += 1

        anomalies = []
        score = 85

        # Low confidence words can indicate altered text
        total_words = len(words)
        if total_words > 0:
            low_ratio = low_conf_count / total_words
            if low_ratio > 0.3:
                anomalies.append(
                    f"{int(low_ratio * 100)}% of detected text has low OCR confidence — possible font substitution or editing"
                )
                score -= int(low_ratio * 40)

        # Check for suspicious patterns
        content_anomalies = _check_content_patterns(text)
        anomalies.extend(content_anomalies)
        score -= len(content_anomalies) * 10

        return {
            "text": text.strip(),
            "words": words,
            "score": max(0, min(100, score)),
            "anomalies": anomalies,
            "available": True,
        }

    except ImportError:
        logger.warning("pytesseract not installed — OCR stage skipped")
        return _ocr_unavailable()
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return _ocr_unavailable()


def _check_content_patterns(text: str) -> list[str]:
    """Check for suspicious content patterns in OCR text."""
    anomalies = []

    # Future dates
    year_matches = re.findall(r"\b20(\d{2})\b", text)
    for yr in year_matches:
        if int(yr) > 30:  # 2030+ in a document issued now is suspicious
            anomalies.append(f"Suspicious future year detected: 20{yr}")
            break

    # Very short text on what should be a detailed document
    if len(text.strip()) < 20:
        anomalies.append("Document contains very little readable text — may be heavily manipulated or low quality")

    return anomalies


def _ocr_unavailable() -> dict:
    """Return neutral result when OCR is unavailable."""
    return {
        "text": "",
        "words": [],
        "score": 75,  # Neutral — don't penalize for missing tool
        "anomalies": [],
        "available": False,
    }
