"""
GuardianLens — Batch Test Script
Generates 40+ synthetic test documents and runs them through the API.

Usage:
    python batch_test.py                    # Run all 42 tests, show summary
    python batch_test.py --count 10         # Run only 10 tests
    python batch_test.py --api http://localhost:8000  # Custom API URL
    python batch_test.py --batch             # Use /api/batch endpoint (faster)
    python batch_test.py --report            # Save JSON report to test_report.json

Documents generated:
    - Aadhaar cards (authentic + forged)
    - PAN cards
    - Kenyan National IDs
    - US Passports
    - Medical Prescriptions
    - Academic Certificates
    - Legal Contracts
    - Edge cases (blank, tiny, large, multi-page)
"""

import argparse
import io
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta

# Force UTF-8 output on Windows to avoid charmap errors with special chars
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import requests
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install requests reportlab pillow numpy")
    sys.exit(1)


API_BASE = "http://localhost:8000"
RESULTS = []


# ─────────────────────────────────────────────────────────────────────────────
# Document generators
# ─────────────────────────────────────────────────────────────────────────────

def make_pdf(label: str, content_fn, authentic: bool = True) -> str:
    """Create a PDF in temp dir, return path."""
    tmp = tempfile.mktemp(suffix=".pdf")
    c = canvas.Canvas(tmp, pagesize=A4)
    content_fn(c, authentic)
    c.save()
    return tmp


def make_image(label: str, content_fn, authentic: bool = True, fmt="jpg") -> str:
    """Create an image doc in temp dir, return path."""
    tmp = tempfile.mktemp(suffix=f".{fmt}")
    img = Image.new("RGB", (800, 600), color=(250, 248, 245))
    draw = ImageDraw.Draw(img)
    content_fn(draw, img, authentic)
    img.save(tmp, quality=92 if fmt == "jpg" else None)
    return tmp


# ── Aadhaar Card ─────────────────────────────────────────────────────────────
def aadhaar_content(draw, img, authentic):
    W, H = img.size
    # Background
    draw.rectangle([0, 0, W, H], fill=(255, 248, 220))
    # Header bar
    draw.rectangle([0, 0, W, 60], fill=(0, 100, 180))
    draw.text((20, 15), "भारत सरकार / Government of India", fill="white")
    draw.text((20, 35), "Unique Identification Authority of India", fill="white")
    # Name
    draw.text((20, 80), "Name: Rajesh Kumar Sharma", fill=(30, 30, 30))
    draw.text((20, 110), "Date of Birth: 15/08/1985", fill=(30, 30, 30))
    draw.text((20, 140), "Gender: Male", fill=(30, 30, 30))
    # Aadhaar number — authentic has correct format, forged has wrong one
    if authentic:
        num = f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"
    else:
        num = f"XXXX-XXXX-{random.randint(1000,9999)}"  # wrong format
    draw.text((20, 180), f"Aadhaar No: {num}", fill=(0, 80, 160))
    # Fake QR placeholder
    draw.rectangle([W-120, H-120, W-20, H-20], fill=(30, 30, 30))
    if not authentic:
        # Add obvious artifact for forged: mismatched color block
        draw.rectangle([200, 100, 320, 200], fill=(255, 0, 0, 180))
        draw.text((210, 140), "ALTERED", fill="white")


# ── PAN Card ─────────────────────────────────────────────────────────────────
def pan_content(draw, img, authentic):
    W, H = img.size
    draw.rectangle([0, 0, W, H], fill=(255, 255, 235))
    draw.rectangle([0, 0, W, 55], fill=(0, 70, 140))
    draw.text((20, 10), "INCOME TAX DEPARTMENT", fill="white")
    draw.text((20, 30), "GOVT OF INDIA", fill="white")
    # PAN number — AAAAA9999A format
    if authentic:
        pan = "ABCDE1234F"
    else:
        pan = "12345ABCDF"  # invalid format
    draw.text((20, 80), f"Permanent Account Number: {pan}", fill=(30, 30, 30))
    draw.text((20, 110), "Name: PRIYA MEHRA", fill=(30, 30, 30))
    draw.text((20, 140), "Father's Name: SURESH MEHRA", fill=(30, 30, 30))
    draw.text((20, 170), "Date of Birth: 20/03/1990", fill=(30, 30, 30))
    if not authentic:
        draw.text((20, 220), "[SIGNATURE REGION CLONED]", fill=(200, 0, 0))


# ── Academic Certificate ──────────────────────────────────────────────────────
def cert_content(c: canvas.Canvas, authentic: bool):
    c.setPageSize(A4)
    W, H = A4
    c.setFillColorRGB(0.95, 0.95, 1.0)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # Border
    c.setStrokeColorRGB(0.2, 0.2, 0.6)
    c.setLineWidth(8)
    c.rect(20, 20, W-40, H-40, fill=0, stroke=1)
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.1, 0.1, 0.5)
    c.drawCentredString(W/2, H-100, "CERTIFICATE OF ACHIEVEMENT")
    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawCentredString(W/2, H-140, "This is to certify that")
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawCentredString(W/2, H-180, "ANANYA KRISHNAN" if authentic else "AN4NYA KR1SHNAN")
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H-220, "has successfully completed the course in")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, H-250, "Advanced Computer Science & AI")
    # Date
    if authentic:
        date_str = "15th March 2024"
    else:
        date_str = "32nd February 2025"  # impossible date
    c.setFont("Helvetica", 11)
    c.drawCentredString(W/2, H-350, f"Date: {date_str}")
    c.drawCentredString(W/2, H-380, "Director of Studies — IIT Bangalore")
    if not authentic:
        c.setFillColorRGB(1, 0, 0)
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, "WARNING: TAMPERED DOCUMENT — FONT MISMATCH DETECTED")


# ── Medical Prescription ──────────────────────────────────────────────────────
def prescription_content(c: canvas.Canvas, authentic: bool):
    W, H = A4
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0, 0.3, 0.6)
    c.drawString(50, H-60, "Dr. Sanjay Mehta, MBBS, MD")
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    if authentic:
        c.drawString(50, H-80, "Reg. No: MCI/12345/2010")
    else:
        c.drawString(50, H-80, "Reg. No: [ALTERED]")
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(50, H-90, W-50, H-90)
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(50, H-120, "Patient: Mohan Das")
    c.drawString(50, H-145, "Age: 45 years    Sex: Male")
    c.drawString(50, H-170, "Date: " + ("12/04/2024" if authentic else "99/99/9999"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, H-210, "Rx:")
    c.setFont("Helvetica", 11)
    c.drawString(70, H-235, "1. Amoxicillin 500mg — 1 tablet TDS x 5 days")
    c.drawString(70, H-260, "2. Pantoprazole 40mg — 1 tablet OD x 7 days")
    if not authentic:
        # Alter a drug name — common forgery
        c.setFillColorRGB(0.8, 0, 0)
        c.drawString(70, H-285, "3. [DRUG NAME ALTERED BY EDITING SOFTWARE]")


# ── US Passport ───────────────────────────────────────────────────────────────
def passport_content(draw, img, authentic):
    W, H = img.size
    draw.rectangle([0, 0, W, H], fill=(240, 240, 220))
    draw.rectangle([0, 0, W, 50], fill=(0, 50, 120))
    draw.text((20, 12), "UNITED STATES OF AMERICA", fill="white")
    draw.text((20, 30), "PASSPORT", fill=(200, 200, 100))
    draw.text((20, 70), "Surname: SMITH", fill=(20, 20, 20))
    draw.text((20, 95), "Given Names: JOHN EDWARD", fill=(20, 20, 20))
    draw.text((20, 120), "Nationality: UNITED STATES OF AMERICA", fill=(20, 20, 20))
    draw.text((20, 145), "Date of Birth: 04 JUL 1980", fill=(20, 20, 20))
    draw.text((20, 170), "Sex: M", fill=(20, 20, 20))
    draw.text((20, 195), "Place of Birth: NEW YORK, USA", fill=(20, 20, 20))
    # MRZ line — authentic has P<USA format
    if authentic:
        mrz = "P<USASMITH<<JOHN<EDWARD<<<<<<<<<<<<<<<<<<<<"
    else:
        mrz = "P<XXXSMITH<<JOHN<EDWARD<<<<<<<<<<<<<<<<<<<<"  # wrong country code
    draw.rectangle([0, H-80, W, H], fill=(245, 245, 230))
    draw.text((10, H-65), mrz, fill=(0, 0, 0))
    draw.text((10, H-45), "1234567890USA8007044M2512315<<<<<<<<<<<<<<<6", fill=(0, 0, 0))
    if not authentic:
        draw.rectangle([300, 60, 450, 200], fill=(255, 200, 200))
        draw.text((310, 120), "PHOTO\nREPLACED", fill=(180, 0, 0))


# ── Kenyan National ID ────────────────────────────────────────────────────────
def kenya_id_content(draw, img, authentic):
    W, H = img.size
    draw.rectangle([0, 0, W, H], fill=(240, 250, 240))
    draw.rectangle([0, 0, W, 55], fill=(0, 100, 0))
    draw.text((20, 10), "REPUBLIC OF KENYA", fill="white")
    draw.text((20, 30), "NATIONAL IDENTITY CARD", fill="white")
    draw.text((20, 75), "Full Name: JOHN KAMAU MWANGI", fill=(20, 20, 20))
    if authentic:
        id_num = str(random.randint(10000000, 99999999))
    else:
        id_num = "ABC-12345"  # wrong format (should be 7-8 digits)
    draw.text((20, 100), f"ID Number: {id_num}", fill=(0, 100, 0))
    draw.text((20, 125), "Date of Birth: 23/06/1992", fill=(20, 20, 20))
    draw.text((20, 150), "Sex: Male", fill=(20, 20, 20))
    draw.text((20, 175), "District of Birth: Nairobi", fill=(20, 20, 20))
    if not authentic:
        draw.text((20, 220), "HARAMBEE [DISTORTED SEAL]", fill=(150, 0, 0))


# ── Legal Contract ────────────────────────────────────────────────────────────
def contract_content(c: canvas.Canvas, authentic: bool):
    W, H = A4
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W/2, H-60, "SERVICE AGREEMENT")
    c.setFont("Helvetica", 11)
    c.drawString(50, H-100, f"This agreement is entered into on {'15th January 2024' if authentic else '30th February 2024'}")
    c.drawString(50, H-120, "between TechCorp Solutions Pvt. Ltd. (\"Service Provider\")")
    c.drawString(50, H-140, "and GlobalTrade Ltd. (\"Client\").")
    c.drawString(50, H-180, "1. SERVICES: The Service Provider agrees to provide software development services.")
    c.drawString(50, H-200, "2. PAYMENT: Client agrees to pay INR 5,00,000 per month.")
    c.drawString(50, H-220, "3. DURATION: This agreement is valid for 12 months from the date above.")
    c.drawString(50, H-340, "Service Provider Signature: _____________________")
    c.drawString(50, H-370, "Client Signature: _____________________")
    if not authentic:
        c.setFillColorRGB(0.7, 0, 0)
        c.drawString(50, H-410, "* SIGNATURE REGION SHOWS CLONING ARTIFACTS — AMOUNT MAY HAVE BEEN ALTERED")


# ─────────────────────────────────────────────────────────────────────────────
# Test document definitions: (name, generator, doc_type, expected_verdict)
# ─────────────────────────────────────────────────────────────────────────────
def build_test_suite():
    tests = []

    # Authentic documents
    for i in range(5):
        tests.append(dict(
            name=f"aadhaar_authentic_{i+1}.jpg",
            gen=lambda a=True: make_image("aadhaar", aadhaar_content, a),
            doc_type="india_aadhaar", authentic=True, expected="AUTHENTIC",
        ))
    for i in range(5):
        tests.append(dict(
            name=f"pan_authentic_{i+1}.jpg",
            gen=lambda a=True: make_image("pan", pan_content, a),
            doc_type="india_pan", authentic=True, expected="AUTHENTIC",
        ))
    for i in range(4):
        tests.append(dict(
            name=f"certificate_authentic_{i+1}.pdf",
            gen=lambda a=True: make_pdf("cert", cert_content, a),
            doc_type="academic_certificate_generic", authentic=True, expected="AUTHENTIC",
        ))
    for i in range(4):
        tests.append(dict(
            name=f"prescription_authentic_{i+1}.pdf",
            gen=lambda a=True: make_pdf("prescription", prescription_content, a),
            doc_type="medical_prescription_india", authentic=True, expected="AUTHENTIC",
        ))
    for i in range(3):
        tests.append(dict(
            name=f"passport_authentic_{i+1}.jpg",
            gen=lambda a=True: make_image("passport", passport_content, a),
            doc_type="us_passport", authentic=True, expected="AUTHENTIC",
        ))
    for i in range(3):
        tests.append(dict(
            name=f"kenya_id_authentic_{i+1}.jpg",
            gen=lambda a=True: make_image("kenya_id", kenya_id_content, a),
            doc_type="kenya_national_id", authentic=True, expected="AUTHENTIC",
        ))
    for i in range(3):
        tests.append(dict(
            name=f"contract_authentic_{i+1}.pdf",
            gen=lambda a=True: make_pdf("contract", contract_content, a),
            doc_type="contract", authentic=True, expected="AUTHENTIC",
        ))

    # Forged documents
    for i in range(5):
        tests.append(dict(
            name=f"aadhaar_forged_{i+1}.jpg",
            gen=lambda a=False: make_image("aadhaar", aadhaar_content, a),
            doc_type="india_aadhaar", authentic=False, expected="FORGED",
        ))
    for i in range(4):
        tests.append(dict(
            name=f"pan_forged_{i+1}.jpg",
            gen=lambda a=False: make_image("pan", pan_content, a),
            doc_type="india_pan", authentic=False, expected="FORGED",
        ))
    for i in range(3):
        tests.append(dict(
            name=f"certificate_forged_{i+1}.pdf",
            gen=lambda a=False: make_pdf("cert", cert_content, a),
            doc_type="academic_certificate_generic", authentic=False, expected="FORGED",
        ))
    for i in range(3):
        tests.append(dict(
            name=f"passport_forged_{i+1}.jpg",
            gen=lambda a=False: make_image("passport", passport_content, a),
            doc_type="us_passport", authentic=False, expected="FORGED",
        ))
    for i in range(3):
        tests.append(dict(
            name=f"prescription_forged_{i+1}.pdf",
            gen=lambda a=False: make_pdf("prescription", prescription_content, a),
            doc_type="medical_prescription_india", authentic=False, expected="FORGED",
        ))
    for i in range(2):
        tests.append(dict(
            name=f"contract_forged_{i+1}.pdf",
            gen=lambda a=False: make_pdf("contract", contract_content, a),
            doc_type="contract", authentic=False, expected="FORGED",
        ))
    for i in range(2):
        tests.append(dict(
            name=f"kenya_id_forged_{i+1}.jpg",
            gen=lambda a=False: make_image("kenya_id", kenya_id_content, a),
            doc_type="kenya_national_id", authentic=False, expected="FORGED",
        ))

    return tests


# ─────────────────────────────────────────────────────────────────────────────
# API interaction
# ─────────────────────────────────────────────────────────────────────────────

def verify_single(file_path: str, filename: str, doc_type: str, expected: str, api_base: str) -> dict:
    """Call /api/verify and return result dict."""
    t = time.monotonic()
    try:
        with open(file_path, "rb") as f:
            ext = Path(file_path).suffix.lower()
            mime = "application/pdf" if ext == ".pdf" else "image/jpeg"
            resp = requests.post(
                f"{api_base}/api/verify",
                files={"file": (filename, f, mime)},
                data={"doc_type": doc_type},
                timeout=90,
            )
        elapsed = time.monotonic() - t

        if resp.status_code == 200:
            data = resp.json()
            verdict = data.get("verdict", "UNKNOWN")
            correct = verdict == expected
            return {
                "filename": filename,
                "doc_type": doc_type,
                "expected": expected,
                "verdict": verdict,
                "trust_score": data.get("trust_score"),
                "confidence": data.get("confidence"),
                "correct": correct,
                "time_s": round(elapsed, 2),
                "scan_id": data.get("scan_id"),
                "status": "ok",
            }
        else:
            return {"filename": filename, "status": "error", "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "time_s": round(elapsed, 2)}
    except Exception as e:
        return {"filename": filename, "status": "error", "error": str(e), "time_s": round(time.monotonic() - t, 2)}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GuardianLens Batch Test Script")
    parser.add_argument("--count", type=int, default=0, help="Limit number of tests (0 = all)")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--report", action="store_true", help="Save JSON report")
    args = parser.parse_args()

    # Check backend
    try:
        r = requests.get(f"{args.api}/api/health", timeout=5)
        health = r.json()
        print(f"\n{'='*60}")
        print(f"  GuardianLens Batch Test Runner")
        print(f"  Backend: {args.api} -- {health.get('status', 'ok').upper()}")
        print(f"  Gemini: {'[OK]' if health.get('gemini_available') else '[X] (mock mode)'}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"ERROR: Backend not reachable at {args.api}: {e}")
        print("Start backend: cd backend && python run.py")
        sys.exit(1)

    tests = build_test_suite()
    if args.count > 0:
        tests = tests[:args.count]

    print(f"  Generating {len(tests)} test documents...\n")

    results = []
    correct = 0
    errors = 0
    tmpfiles = []

    for i, test in enumerate(tests, 1):
        file_path = test["gen"]()
        tmpfiles.append(file_path)

        print(f"  [{i:02d}/{len(tests)}] {test['name']:<40} ", end="", flush=True)

        r = verify_single(file_path, test["name"], test["doc_type"], test["expected"], args.api)
        results.append(r)

        if r["status"] == "ok":
            mark = "[OK]" if r["correct"] else "[X] "
            print(f"{mark} {r['verdict']:<12} score={r['trust_score']:>3}  ({r['time_s']}s)")
            if r["correct"]:
                correct += 1
        else:
            print(f"ERROR: {r.get('error', 'unknown')[:60]}")
            errors += 1

    # Cleanup temp files
    for f in tmpfiles:
        try:
            os.unlink(f)
        except Exception:
            pass

    # Summary
    total = len(results)
    ok = total - errors
    accuracy = (correct / ok * 100) if ok > 0 else 0
    avg_time = sum(r.get("time_s", 0) for r in results) / total if total else 0

    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Total tested:     {total}")
    print(f"  Successful calls: {ok}")
    print(f"  Errors:           {errors}")
    print(f"  Correct verdicts: {correct}/{ok} ({accuracy:.1f}%)")
    print(f"  Avg time/doc:     {avg_time:.1f}s")
    print(f"  Total time:       {sum(r.get('time_s',0) for r in results):.1f}s")

    # Verdict breakdown
    auth = sum(1 for r in results if r.get("verdict") == "AUTHENTIC")
    susp = sum(1 for r in results if r.get("verdict") == "SUSPICIOUS")
    forg = sum(1 for r in results if r.get("verdict") == "FORGED")
    print(f"\n  Verdict breakdown:")
    print(f"    AUTHENTIC:  {auth}")
    print(f"    SUSPICIOUS: {susp}")
    print(f"    FORGED:     {forg}")
    print(f"{'='*60}\n")

    if args.report:
        report = {
            "run_at": datetime.utcnow().isoformat(),
            "api": args.api,
            "total": total,
            "accuracy_pct": round(accuracy, 2),
            "avg_time_s": round(avg_time, 2),
            "results": results,
        }
        report_path = Path("test_report.json")
        report_path.write_text(json.dumps(report, indent=2))
        print(f"  Report saved: {report_path.absolute()}\n")


if __name__ == "__main__":
    main()
