"""
GuardianLens — Live API Test Script
Tests the verify endpoint with real documents.
Run: python test_live_api.py
"""
import urllib.request
import urllib.error
import json
import os
import sys

API_BASE = "http://127.0.0.1:8000"
BOUNDARY = "GuardianLensBoundary12345"


def test_health():
    print("\n=== HEALTH CHECK ===")
    try:
        r = urllib.request.urlopen(f"{API_BASE}/api/health", timeout=5)
        data = json.loads(r.read())
        print(f"  Status  : {data['status']}")
        print(f"  DB      : {data['database']}")
        print(f"  Gemini  : {'LIVE' if data['gemini_available'] else 'Mock mode'}")
        return True
    except Exception as e:
        print(f"  FAILED  : {e}")
        print("  Make sure the backend is running: cd backend && python run.py")
        return False


def verify_document(filepath, doc_type="other"):
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_data = f.read()

    content_type = "image/jpeg" if filepath.endswith((".jpg", ".jpeg")) else "image/png"

    body = (
        f"--{BOUNDARY}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_data + (
        f"\r\n--{BOUNDARY}\r\n"
        f"Content-Disposition: form-data; name=\"doc_type\"\r\n\r\n"
        f"{doc_type}\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{API_BASE}/api/verify",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
        method="POST",
    )

    r = urllib.request.urlopen(req, timeout=60)
    return json.loads(r.read())


def run_tests():
    if not test_health():
        sys.exit(1)

    test_files = [
        ("tests/fixtures/authentic/sample_id.jpg", "other"),
        ("tests/fixtures/forged/forged_id.jpg", "other"),
    ]

    print("\n=== VERIFY TESTS ===")
    for filepath, doc_type in test_files:
        if not os.path.exists(filepath):
            print(f"  SKIP: {filepath} (not found)")
            continue

        print(f"\n  File    : {os.path.basename(filepath)}")
        try:
            data = verify_document(filepath, doc_type)
            verdict_icon = {"AUTHENTIC": "[OK]", "SUSPICIOUS": "[??]", "FORGED": "[!!]"}.get(data["verdict"], "[--]")
            print(f"  {verdict_icon} VERDICT   : {data['verdict']}")
            print(f"     SCORE    : {data['trust_score']}/100")
            print(f"     CONFIDENCE: {data['confidence']}")
            print(f"     AI MODEL : {data['ai_model_used']}")
            print(f"     TIME     : {data['processing_time_ms']}ms")
            print(f"     ANOMALIES: {len(data.get('anomalies', []))}")
            for a in data.get("anomalies", []):
                print(f"       - {a}")
            print(f"     HEATMAP  : {data.get('ela_heatmap_url')}")
            print(f"     CERT     : {data.get('certificate_url')}")
        except urllib.error.HTTPError as e:
            print(f"  ERROR : {e.code} - {e.read().decode()}")
        except Exception as e:
            print(f"  ERROR : {e}")

    print("\n=== HISTORY ===")
    try:
        r = urllib.request.urlopen(f"{API_BASE}/api/history", timeout=5)
        data = json.loads(r.read())
        print(f"  Total scans in DB: {data['total']}")
        for s in data.get("scans", []):
            icon = {"AUTHENTIC": "OK", "SUSPICIOUS": "??", "FORGED": "!!"}.get(s["verdict"], "--")
            print(f"  [{icon}] {s['filename']:<35} score={s['trust_score']} verdict={s['verdict']}")
    except Exception as e:
        print(f"  ERROR : {e}")

    print("\n=== DONE ===\n")


if __name__ == "__main__":
    run_tests()
