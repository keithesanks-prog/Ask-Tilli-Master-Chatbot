# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (build/runtime minimal)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer cache
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

# Copy source
COPY app /app/app
COPY README.md /app/README.md

# Create non-root user
RUN useradd -m -u 10001 master && chown -R master:master /app
USER master

# Default environment (override at runtime)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    TEST_MODE=false

EXPOSE 8000

# Healthcheck (basic)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


