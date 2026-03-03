# ============================================
# Stage 1: Dependency builder (cached layer)
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual env
COPY requirements-prod.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements-prod.txt

# ============================================
# Stage 2: Production runtime (minimal image)
# ============================================
FROM python:3.11-slim

LABEL maintainer="Erkan"
LABEL description="Minibar Takip Sistemi"

WORKDIR /app

# Runtime-only system dependencies (no gcc, no dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# ML models directory
RUN mkdir -p /app/ml_models && chmod 755 /app/ml_models

# Entrypoint
RUN chmod +x docker-entrypoint.sh

# Security: non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

VOLUME ["/app/ml_models"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:5000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
