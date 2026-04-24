"""
GuardianLens — Jurisdiction-Aware Document Templates
Provides known forgery signals for 6+ document types used in Gemini prompts.
"""

DOCUMENT_TEMPLATES: dict[str, dict] = {
    "india_aadhaar": {
        "description": "Indian Aadhaar card issued by UIDAI",
        "expected_fonts": ["Noto Sans", "Arial"],
        "qr_position": "bottom-right",
        "id_format": r"^\d{4}\s\d{4}\s\d{4}$",
        "seal": "UIDAI lion capital emblem",
        "forgery_signals": [
            "Aadhaar number font mismatch from Noto Sans",
            "QR code missing or wrong position (should be bottom-right)",
            "Photo background not uniform grey",
            "Date of Birth not in DD/MM/YYYY format",
            "UIDAI logo distorted or pixelated",
            "Address field font inconsistency",
        ],
    },
    "india_pan": {
        "description": "Indian PAN card — Income Tax Department",
        "id_format": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
        "seal": "Income Tax Department emblem",
        "forgery_signals": [
            "PAN format incorrect (should be XXXXX9999X)",
            "Income Tax Department seal distorted",
            "Signature field altered or missing",
            "Hologram strip absent or flat-looking",
            "Font inconsistency in name/father name fields",
        ],
    },
    "kenya_national_id": {
        "description": "Kenyan National Identity Card",
        "id_format": r"^\d{7,8}$",
        "seal": "Kenyan coat of arms with Harambee text",
        "forgery_signals": [
            "Serial number format incorrect (should be 7-8 digits)",
            "Harambee coat of arms distorted or missing",
            "Laminate artifacts or reflection anomalies",
            "Photo substitution visible (edge artifacts around photo)",
            "Date format inconsistency",
        ],
    },
    "us_passport": {
        "description": "United States Passport",
        "mrz_pattern": "P<USA",
        "expected_fonts": ["OCR-B"],
        "forgery_signals": [
            "MRZ (Machine Readable Zone) format incorrect",
            "Eagle seal asymmetry detected",
            "Passport number font mismatch from OCR-B standard",
            "UV-reactive elements appear flat in visible light scan",
            "Page number/issue date inconsistency",
        ],
    },
    "medical_prescription_india": {
        "description": "Indian Medical Prescription",
        "forgery_signals": [
            "Doctor registration number missing or incorrect format (MCI/state council)",
            "Signature pixel inconsistency (copy-pasted signature)",
            "Date in future or logically inconsistent",
            "Drug name altered post-signing (different compression artifacts)",
            "Clinic letterhead font mismatch",
            "Dosage/quantity field shows signs of digital editing",
        ],
    },
    "academic_certificate_generic": {
        "description": "Generic Academic Certificate / Degree",
        "forgery_signals": [
            "University seal pixelated or geometric distortion",
            "Font mismatch in student name or grade fields",
            "Embossed seal appears flat (2D, no depth)",
            "Signature baseline inconsistent with surrounding text",
            "Date/year inconsistency with stated course duration",
            "Paper texture pattern shows copy-paste artifacts",
        ],
    },
    "contract": {
        "description": "Legal Contract / Agreement",
        "forgery_signals": [
            "Signature appears copy-pasted (uniform edge, no pressure variation)",
            "Clause text shows different JPEG compression than rest of document",
            "Page numbering inconsistency",
            "Notary stamp shows digital insertion artifacts",
            "Font inconsistency between original and amended sections",
        ],
    },
    "other": {
        "description": "Generic document",
        "forgery_signals": [
            "Visual inconsistencies in fonts or layouts",
            "Signs of digital manipulation or copy-pasting",
            "Compression artifacts inconsistent across regions",
            "Seal or signature irregularities",
        ],
    },
}


def get_jurisdiction_context(doc_type: str) -> str:
    """
    Build jurisdiction context string for Gemini prompt injection.
    Returns empty string for unknown doc types.
    """
    template = DOCUMENT_TEMPLATES.get(doc_type) or DOCUMENT_TEMPLATES.get("other")
    if not template:
        return ""

    signals = "\n".join(f"- {s}" for s in template.get("forgery_signals", []))
    return (
        f"DOCUMENT TYPE: {template['description']}\n"
        f"KNOWN FORGERY SIGNALS FOR THIS DOCUMENT TYPE:\n{signals}"
    )


def detect_doc_type(filename: str, ocr_text: str = "") -> str:
    """
    Heuristic doc type detection based on filename and OCR text.
    Returns a DOCUMENT_TEMPLATES key.
    """
    fname = filename.lower()
    text = ocr_text.lower()

    if any(k in fname or k in text for k in ["aadhaar", "aadhar", "uid", "uidai"]):
        return "india_aadhaar"
    if any(k in fname or k in text for k in ["pan", "income tax", "permanent account"]):
        return "india_pan"
    if any(k in fname or k in text for k in ["kenya", "kenyan", "harambee"]):
        return "kenya_national_id"
    if any(k in fname or k in text for k in ["passport", "usa", "united states"]):
        return "us_passport"
    if any(k in fname or k in text for k in ["prescription", "rx", "medicine", "tablet", "mg"]):
        return "medical_prescription_india"
    if any(k in fname or k in text for k in ["degree", "certificate", "university", "graduate", "bachelor"]):
        return "academic_certificate_generic"
    if any(k in fname or k in text for k in ["contract", "agreement", "hereby", "parties"]):
        return "contract"
    return "other"
