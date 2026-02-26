# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.prod.txt ./
RUN pip install --prefix=/install -r requirements.prod.txt

# ─── Stage 2: Runner ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Runtime: Pillow libs + curl (healthcheck) + gosu (rootless runtime via privilege drop)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg-dev \
        libpng-dev \
        curl \
        gosu \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (UID/GID 1000) — process runs as appuser after entrypoint init
RUN groupadd -g 1000 appuser && \
    useradd  -u 1000 -g appuser -s /bin/bash -m appuser

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source (owned by appuser so Django can read it)
COPY --chown=appuser:appuser . .

# Entrypoint runs as root to initialize volume directories, then drops to appuser via gosu
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Container starts as root so entrypoint can init volumes; gosu drops to appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
