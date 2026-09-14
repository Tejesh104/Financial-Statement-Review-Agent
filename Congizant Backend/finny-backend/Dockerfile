# Production Dockerfile for FINNY Financial Statement Review Backend
# Python 3.11 slim base image for optimal performance and container size
FROM python:3.11-slim

# Set system environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8001 \
    APP_ENV=production

# Install essential OS-level dependencies for PyMuPDF, pdfplumber, and PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code and pre-trained ML models
COPY app/ ./app/
COPY ml_models/ ./ml_models/
COPY run.py .

# Create directory for runtime document processing & file uploads
RUN mkdir -p uploads

# Expose backend port
EXPOSE 8001

# Health check to ensure container is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Start FastAPI production server via Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --workers 2"]
