<div align="center">

# 🛡️ GuardianLens

### AI-Powered Document Authentication Platform

**Google Solution Challenge 2026 · SDG 16 — Peace, Justice and Strong Institutions**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Gemini-1.5%20Flash-4285F4?logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> Upload any document → get a **forensic Trust Score**, **ELA heatmap**, and **signed PDF certificate** in under 10 seconds.

![GuardianLens Demo](frontend/assets/hero.png)

</div>

---

## ✨ What It Does

GuardianLens runs a **7-stage forensic pipeline** on every uploaded document:

| Stage | Module | What it checks |
|-------|--------|---------------|
| 1 | **ELA** | Error Level Analysis — detects re-saved/edited regions |
| 2 | **Metadata** | EXIF timestamps, PDF creation metadata, software fingerprints |
| 3 | **OCR** | Tesseract text extraction for content logic checks |
| 4 | **Jurisdiction** | Document-type-specific format rules (ID numbers, dates, seals) |
| 5 | **Gemini Vision** | AI visual inspection — fonts, seals, clone-stamp artifacts |
| 6 | **Scorer** | Weighted ensemble → Trust Score 0–100 |
| 7 | **Certificate** | Signed PDF certificate of authenticity via ReportLab |

**Supported documents:** Aadhaar, PAN, Kenyan National ID, US Passport, Medical Prescriptions, Academic Certificates, Legal Contracts.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- (Optional) [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text extraction
- (Optional) [Poppler](https://poppler.freedesktop.org/) for PDF rendering

### 1 — Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your Gemini API key (get one free at https://aistudio.google.com)

# Start server
python run.py
# ✅ API running at   http://localhost:8000
# ✅ Swagger UI at    http://localhost:8000/docs
# ✅ ReDoc at         http://localhost:8000/redoc
```

### 2 — Frontend

Open `frontend/index.html` directly in your browser — **no build step required**.

| File | Purpose |
|------|---------|
| `frontend/index.html` | Upload zone + document type selector |
| `frontend/result.html` | Live results — Trust Score ring, ELA heatmap, breakdown |
| `frontend/dashboard.html` | Full scan history with filters |

---

## 🐳 Docker

```bash
# From project root
docker-compose up --build

# Backend: http://localhost:8000
```

---

## 🔑 Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
# Required for AI analysis (free tier available)
GEMINI_API_KEY=your_gemini_api_key_here   # https://aistudio.google.com

# Database (SQLite by default, swap to PostgreSQL URL for production)
DATABASE_URL=sqlite+aiosqlite:///./guardianlens.db

# App
APP_ENV=development
SECRET_KEY=change-this-in-production

# Limits
MAX_FILE_SIZE_MB=10
RATE_LIMIT_PER_MINUTE=20
```

> **No API key?** The system runs in **mock mode** — produces realistic forensic scores without calling Gemini. Perfect for local testing.

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/verify` | Upload + authenticate a document |
| `GET` | `/api/history` | Paginated scan history |
| `GET` | `/api/scan/{id}` | Full result for a single scan |
| `GET` | `/api/heatmap/{id}` | ELA forensic heatmap (PNG) |
| `GET` | `/api/cert/{id}` | PDF authentication certificate |
| `POST` | `/api/batch` | Batch verify multiple documents |
| `GET` | `/api/health` | System health check |
| `GET` | `/docs` | Interactive Swagger UI |

### Example — Verify a Document

```bash
curl -X POST http://localhost:8000/api/verify \
  -F "file=@/path/to/document.jpg" \
  -F "doc_type=india_aadhaar"
```

**Response:**
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "trust_score": 23,
  "verdict": "FORGED",
  "confidence": 0.94,
  "breakdown": {
    "metadata_integrity": 45,
    "visual_consistency": 12,
    "content_coherence": 18,
    "font_analysis": 20,
    "seal_stamp_check": 10
  },
  "anomalies": [
    "High ELA error level in signature region",
    "Font substitution detected in name field",
    "Seal stamp shows transparency halo artifact"
  ],
  "ela_heatmap_url": "/api/heatmap/550e8400...",
  "certificate_url": "/api/cert/550e8400...",
  "processing_time_ms": 2847
}
```

---

## 🧪 Batch Testing

The included `batch_test.py` generates **49 synthetic test documents** (authentic + forged) and runs them through the full pipeline:

```bash
# Quick test (5 docs)
python batch_test.py --count 5

# Full suite (49 docs) + save JSON report
python batch_test.py --report

# Custom API URL
python batch_test.py --api http://localhost:8000 --report
```

**Document types tested:** Aadhaar, PAN, Academic Certificates, Medical Prescriptions, US Passport, Kenyan National ID, Legal Contracts.

---

## 🏗️ Project Structure

```
GuardianLens/
├── frontend/
│   ├── index.html          ← Upload page
│   ├── result.html         ← Scan results (score ring, heatmap)
│   └── dashboard.html      ← Scan history
│
├── backend/
│   ├── run.py              ← Server entry point (uvicorn)
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── app/
│       ├── main.py         ← FastAPI app + CORS + lifespan
│       ├── config.py       ← Pydantic settings
│       ├── database.py     ← SQLAlchemy async engine
│       ├── api/
│       │   ├── verify.py   ← POST /api/verify
│       │   ├── history.py  ← GET /api/history
│       │   ├── certs.py    ← GET /api/cert, /api/heatmap
│       │   ├── health.py   ← GET /api/health
│       │   └── batch.py    ← POST /api/batch
│       ├── core/
│       │   ├── pipeline.py       ← 7-stage orchestrator
│       │   ├── ela.py            ← Error Level Analysis
│       │   ├── gemini.py         ← Gemini Vision + mock fallback
│       │   ├── jurisdiction.py   ← Document-type rules
│       │   ├── metadata.py       ← EXIF/PDF forensics
│       │   ├── ocr.py            ← Tesseract OCR
│       │   ├── scorer.py         ← Weighted ensemble scoring
│       │   └── cert_generator.py ← PDF certificates (ReportLab)
│       └── models/
│           └── scan.py           ← SQLAlchemy Scan model
│
├── batch_test.py           ← Synthetic batch testing script
├── serve_frontend.py       ← Simple local frontend server
├── docker-compose.yml
└── README.md
```

---

## 🌍 SDG 16 Impact

GuardianLens directly addresses **SDG 16.9 — Legal identity for all**:

- 🏥 **Healthcare** — Detects forged prescriptions for Schedule H/controlled drugs
- 🎓 **Education** — Catches fake degree certificates undermining fair hiring
- 💰 **Finance** — Flags forged income documents used in loan fraud
- 🪪 **Identity** — Authenticates national IDs used for government services access

Document fraud disproportionately harms people in emerging markets — GuardianLens puts forensic-grade authentication in every institution's hands.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

<div align="center">

Built with ❤️ for the **Google Solution Challenge 2026**

</div>
