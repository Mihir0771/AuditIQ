# Production Multi-Stage Dockerfile for AuditIQ Enterprise Engine
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install system utilities and Playwright headless Chromium dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 || libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy package specifications
COPY pyproject.toml ./
COPY README.md ./

# Install python dependencies and auditiq in editable mode
RUN pip install --upgrade pip && \
    pip install . && \
    playwright install chromium && \
    playwright install-deps chromium || true

# Copy full application source and configurations
COPY config/ ./config/
COPY src/ ./src/

# Install the application package
RUN pip install -e . --no-deps

# Create runtime directories
RUN mkdir -p reports research/outputs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/system/doctor || exit 1

CMD ["uvicorn", "auditiq.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
