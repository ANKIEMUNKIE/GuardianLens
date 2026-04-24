"""
GuardianLens — FastAPI Application
Google Solution Challenge 2026 · SDG 16 — Peace, Justice and Strong Institutions

Run with: python run.py  (or uvicorn app.main:app --reload from /backend)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api import verify, history, health, certs, batch

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup/shutdown) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    logger.info("GuardianLens starting up...")
    await init_db()
    logger.info("Database initialized ✓")
    logger.info(f"Gemini AI: {'✓ available' if settings.GEMINI_API_KEY else '⚠ mock mode (no API key)'}")
    logger.info(f"Upload dir: {settings.UPLOAD_DIR}")
    logger.info("GuardianLens ready 🛡")
    yield
    logger.info("GuardianLens shutting down...")


# ── App Instance ──────────────────────────────────────────────
app = FastAPI(
    title="GuardianLens API",
    description=(
        "AI-powered document authentication API. "
        "Upload any document — national ID, prescription, certificate, contract — "
        "and receive a forensic Trust Score, ELA heatmap, and signed PDF certificate. "
        "Google Solution Challenge 2026 · SDG 16."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
# allow_origins=["*"] + allow_credentials=False is required to support:
#  - file:// origins (null origin) when frontend is opened from disk
#  - HTTP origins when served via a local dev server
# We also add specific origins so allow_credentials can be True for them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Static File Serving ───────────────────────────────────────
# Serve generated files (heatmaps, certs) as static files during dev
try:
    app.mount("/static/heatmaps", StaticFiles(directory=str(settings.HEATMAP_DIR)), name="heatmaps")
    app.mount("/static/certs", StaticFiles(directory=str(settings.CERT_DIR)), name="certs")
except Exception:
    pass  # Dirs may not exist yet — created on first request

# ── API Routes ────────────────────────────────────────────────
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(verify.router, prefix="/api", tags=["Verification"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(certs.router, prefix="/api", tags=["Certificates"])
app.include_router(batch.router, prefix="/api", tags=["Batch"])


# ── Root ──────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "GuardianLens API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "sdg": "SDG 16 — Peace, Justice and Strong Institutions",
        "endpoints": {
            "verify": "POST /api/verify",
            "history": "GET /api/history",
            "scan": "GET /api/scan/{scan_id}",
            "heatmap": "GET /api/heatmap/{scan_id}",
            "certificate": "GET /api/cert/{scan_id}",
            "health": "GET /api/health",
        },
    }


# ── Global Exception Handler ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
