# GuardianLens Backend — Dockerfile
# Supports local dev and Google Cloud Run deployment

FROM python:3.12-slim

# System dependencies for Pillow, pdf2image, pytesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p uploads heatmaps certificates

# Cloud Run expects PORT env var; default 8000 for local
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
