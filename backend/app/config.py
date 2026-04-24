"""
GuardianLens — Configuration
Reads from environment variables / .env file
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_NAME: str = "GuardianLens"
    SECRET_KEY: str = "guardianlens-dev-secret-change-in-production-32chars"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:7890",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://localhost:5501",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:5173",
        "http://127.0.0.1:7890",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8080",
        "null",
        "*",
    ]

    # Database (default: SQLite for zero-infra local dev)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/guardianlens.db"

    # Google Gemini AI (primary — kept for Google hackathon judging)
    GEMINI_API_KEY: str = ""

    # Groq AI (fast free fallback — llama-3.2-vision, ~10x faster than Gemini)
    GROQ_API_KEY: str = ""

    # File Storage (local paths)
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    HEATMAP_DIR: Path = BASE_DIR / "heatmaps"
    CERT_DIR: Path = BASE_DIR / "certificates"

    # Limits
    MAX_FILE_SIZE_MB: int = 10
    RATE_LIMIT_PER_MINUTE: int = 20

    # Features
    SCAN_RETENTION_DAYS: int = 90
    MOCK_GEMINI_IF_NO_KEY: bool = True  # graceful fallback

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Ensure directories exist
for d in [settings.UPLOAD_DIR, settings.HEATMAP_DIR, settings.CERT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
