"""
GuardianLens — Groq Vision Fallback
Fast, free AI analysis using LLaMA 3.2 Vision via Groq's OpenAI-compatible API.

This is the SECONDARY fallback:
  Gemini (primary, Google hackathon) → Groq (fast free fallback) → Mock (offline)

Groq's llama-3.2-11b-vision-preview is ~10x faster than Gemini Flash
and has a generous free tier (30 req/min, 14400 req/day).

Get a free key: https://console.groq.com
Add to .env: GROQ_API_KEY=gsk_xxx...
"""
import asyncio
import base64
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.2-11b-vision-preview"
GROQ_TIMEOUT = 25  # seconds — Groq is fast, so 25s is plenty


GROQ_SYSTEM_PROMPT = """You are GuardianLens, a forensic document authentication AI.
Analyze the document image for signs of digital forgery or tampering.
Return ONLY valid JSON — no markdown, no explanation."""

GROQ_USER_PROMPT = """Analyze this document image for authenticity. Check:
1. Pixel anomalies, JPEG compression inconsistencies, clone-stamp artifacts
2. Font substitution, baseline misalignment, mixed typefaces
3. Seal/stamp geometry, halo artifacts suggesting digital insertion
4. Content logic: date consistency, ID number format, field alignment
5. ELA context: high-error regions flagged at: {ELA_REGIONS}

{JURISDICTION_CONTEXT}

Return ONLY this JSON object:
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
  "doc_type_detected": "<document type string>"
}}"""


async def analyze_with_groq(
    image_path: str,
    jurisdiction_context: str = "",
    ela_regions: list = None,
    api_key: str = "",
) -> Optional[dict]:
    """
    Analyze document with Groq's LLaMA 3.2 Vision — fast free fallback.
    Returns same dict shape as analyze_with_gemini() or None on failure.
    """
    if not api_key:
        return None

    try:
        import httpx

        # Encode image to base64
        img_bytes = Path(image_path).read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()

        # Determine MIME type
        suffix = Path(image_path).suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"

        # Format ELA regions
        ela_summary = "No high-error regions detected"
        if ela_regions:
            parts = [f"({r['x']},{r['y']}) size {r['w']}x{r['h']}, severity {r['severity']:.1f}"
                     for r in ela_regions[:3]]
            ela_summary = "; ".join(parts)

        user_content = GROQ_USER_PROMPT.format(
            ELA_REGIONS=ela_summary,
            JURISDICTION_CONTEXT=jurisdiction_context or "No specific document type context.",
        )

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{img_b64}"},
                        },
                        {"type": "text", "text": user_content},
                    ],
                },
            ],
            "max_tokens": 800,
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=GROQ_TIMEOUT) as client:
            resp = await client.post(
                GROQ_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.error(f"Groq API error {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        raw_text = re.sub(r"```json\s*", "", raw_text)
        raw_text = re.sub(r"```\s*", "", raw_text)

        result = json.loads(raw_text)
        logger.info(
            f"Groq returned trust_score={result.get('trust_score')} verdict={result.get('verdict')}"
        )
        return result

    except asyncio.TimeoutError:
        logger.error(f"Groq API timed out after {GROQ_TIMEOUT}s")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Groq returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return None
