"""
GuardianLens — Gemini Vision Analysis
Primary AI model for document visual forensics.
Falls back to mock scoring if no API key is configured.

SDK: google-genai (new, replaces deprecated google-generativeai)
Model: gemini-2.0-flash-lite (highest free-tier quota)
"""
import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

# Thread pool for blocking Gemini SDK calls
_executor = ThreadPoolExecutor(max_workers=4)
GEMINI_TIMEOUT_SECONDS = 12   # Fail fast → mock results in ~12s max
# gemini-2.0-flash-lite: highest free-tier quota (best for hackathon)
GEMINI_MODEL = "gemini-2.0-flash-lite"


GEMINI_PROMPT_TEMPLATE = """
You are GuardianLens, a forensic document authentication AI specializing in digital forgery detection.

{JURISDICTION_CONTEXT}

Analyze this document image for authenticity. Examine:

1. VISUAL INTEGRITY: Pixel-level anomalies, JPEG compression inconsistencies between regions,
   clone-stamp artifacts, copy-paste seams, noise pattern irregularities.

2. FONT ANALYSIS: Font substitution between editing tools, inconsistent baseline alignment,
   character spacing irregularities, mixed font families within the same field.

3. SEAL & STAMP: Circular seal geometry, ink saturation distribution, rasterization artifacts
   suggesting digital insertion, transparency or halo effects around official stamps.

4. CONTENT LOGIC: Date consistency, ID number format validity, field alignment,
   name/address formatting conventions for this document type.

5. ELA CONTEXT: The ELA forensic analysis has flagged high-error regions at: {ELA_REGIONS_SUMMARY}.
   Specifically examine these coordinates in your visual analysis.

Return ONLY a valid JSON object (no markdown, no preamble, no explanation):
{{
  "trust_score": <integer 0-100>,
  "verdict": "<AUTHENTIC|SUSPICIOUS|FORGED>",
  "confidence": <float 0.0-1.0>,
  "breakdown": {{
    "metadata_integrity": <integer 0-100>,
    "visual_consistency": <integer 0-100>,
    "content_coherence": <integer 0-100>,
    "font_analysis": <integer 0-100>,
    "seal_stamp_check": <integer 0-100>
  }},
  "anomalies": ["<specific finding>", ...],
  "summary": "<2-3 sentence plain English explanation>",
  "doc_type_detected": "<detected document type string>"
}}
""".strip()


async def analyze_with_gemini(
    image_path: str,
    jurisdiction_context: str = "",
    ela_regions: list[dict] = None,
    api_key: str = "",
) -> Optional[dict]:
    """
    Send document image to Gemini Vision for forensic analysis.

    Args:
        image_path: path to document image (JPEG/PNG)
        jurisdiction_context: string from jurisdiction.get_jurisdiction_context()
        ela_regions: list of ELA tampering regions for context
        api_key: Gemini API key

    Returns:
        dict with trust_score, verdict, breakdown, anomalies, summary
        or None on failure
    """
    if not api_key:
        logger.info("No Gemini API key — using mock analysis")
        return None

    try:
        # New google-genai SDK (replaces deprecated google-generativeai)
        from google import genai

        client = genai.Client(api_key=api_key)

        # Format ELA region summary for prompt
        ela_summary = "No high-error regions detected"
        if ela_regions:
            parts = []
            for r in ela_regions[:3]:  # top 3 regions
                parts.append(f"({r['x']},{r['y']}) size {r['w']}x{r['h']}, severity {r['severity']:.1f}")
            ela_summary = "; ".join(parts)

        prompt = GEMINI_PROMPT_TEMPLATE.format(
            JURISDICTION_CONTEXT=jurisdiction_context or "No specific document type context available.",
            ELA_REGIONS_SUMMARY=ela_summary,
        )

        # Load image (blocking I/O — OK here, file is local)
        from PIL import Image
        img = Image.open(image_path)

        # Run blocking Gemini SDK call in thread pool so we don't stall the event loop
        def _call_gemini():
            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt, img],
            )

        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(_executor, _call_gemini),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )

        raw_text = response.text.strip()

        # Parse JSON — strip any markdown fences if present
        raw_text = re.sub(r"```json\s*", "", raw_text)
        raw_text = re.sub(r"```\s*", "", raw_text)

        result = json.loads(raw_text)
        logger.info(f"Gemini returned trust_score={result.get('trust_score')} verdict={result.get('verdict')}")
        return result

    except asyncio.TimeoutError:
        logger.error(f"Gemini API timed out after {GEMINI_TIMEOUT_SECONDS}s — falling back to mock")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        return None
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate" in err_str:
            logger.warning("Gemini quota/rate-limit hit — falling back immediately")
        elif "403" in err_str or "api_key_invalid" in err_str or "invalid" in err_str:
            logger.warning("Gemini API key invalid or unauthorized — falling back to mock")
        elif "network" in err_str or "connect" in err_str or "ssl" in err_str:
            logger.warning(f"Gemini network error: {e} — falling back")
        else:
            logger.error(f"Gemini API call failed: {e}")
        return None


def generate_mock_analysis(
    ela_score: int,
    metadata_score: int,
    filename: str,
    doc_type: str = "other",
) -> dict:
    """
    Deterministic mock analysis used when Gemini API is unavailable.
    Generates plausible scores based on ELA and metadata results.
    Used for demo/development mode.
    """
    import random

    # Seed with filename hash for consistent results
    rng = random.Random(hash(filename))

    # Add some variance around ELA score
    visual = max(0, min(100, ela_score + rng.randint(-15, 15)))
    font = max(0, min(100, ela_score + rng.randint(-10, 20)))
    seal = max(0, min(100, ela_score + rng.randint(-20, 10)))
    content = max(0, min(100, (ela_score + metadata_score) // 2 + rng.randint(-10, 10)))

    # Weighted ensemble
    trust_score = int(
        metadata_score * 0.15 +
        ela_score * 0.35 +
        visual * 0.20 +
        font * 0.20 +
        content * 0.10
    )
    trust_score = max(0, min(100, trust_score))

    verdict = _score_to_verdict(trust_score)
    anomalies = _generate_mock_anomalies(trust_score, doc_type, rng)

    summary = _generate_mock_summary(trust_score, verdict, anomalies)

    return {
        "trust_score": trust_score,
        "verdict": verdict,
        "confidence": round(0.6 + rng.random() * 0.35, 2),
        "breakdown": {
            "metadata_integrity": metadata_score,
            "visual_consistency": visual,
            "content_coherence": content,
            "font_analysis": font,
            "seal_stamp_check": seal,
        },
        "anomalies": anomalies,
        "summary": summary,
        "doc_type_detected": doc_type,
    }


def _score_to_verdict(score: int) -> str:
    if score >= 75:
        return "AUTHENTIC"
    elif score >= 45:
        return "SUSPICIOUS"
    return "FORGED"


def _generate_mock_anomalies(trust_score: int, doc_type: str, rng) -> list[str]:
    all_anomalies = {
        "AUTHENTIC": [],
        "SUSPICIOUS": [
            "Slight compression inconsistency in signature region",
            "Minor font baseline deviation in name field",
            "Seal geometry marginally asymmetric",
        ],
        "FORGED": [
            "High ELA error level detected in signature region",
            "JPEG compression artifacts inconsistent between photo and text regions",
            "Font substitution detected — multiple typefaces in single field",
            "Seal stamp shows digital insertion artifacts (transparency halo)",
            "Clone-stamp pattern detected in background region",
        ],
    }
    verdict = _score_to_verdict(trust_score)
    pool = all_anomalies[verdict]
    if not pool:
        return []
    count = rng.randint(1, min(3, len(pool)))
    return rng.sample(pool, count)


def _generate_mock_summary(trust_score: int, verdict: str, anomalies: list[str]) -> str:
    if verdict == "AUTHENTIC":
        return (
            "Document shows no signs of tampering or digital manipulation. "
            "Metadata timestamps are consistent with stated document origin. "
            "Font rendering and seal geometry match expected institutional patterns."
        )
    elif verdict == "SUSPICIOUS":
        return (
            f"Document contains {len(anomalies)} minor irregularities that warrant manual review. "
            "Some forensic indicators are ambiguous and may be caused by image compression or scanning artifacts. "
            "Recommend verification against the issuing authority before accepting this document."
        )
    else:
        return (
            f"Strong indicators of digital forgery detected. {anomalies[0] if anomalies else 'Multiple anomalies found'}. "
            "ELA analysis reveals significant error level spikes inconsistent with authentic documents. "
            "This document should be rejected and the case escalated for investigation."
        )
