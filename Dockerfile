# --------------------------------------------------------------------------
# Electrician Log MVP — single-container image
# Flask serves the API + frontend static files on port 5000.
#
# Multi-stage build:
#   1. builder  — installs gcc + dev headers, compiles pyvips CFFI extension
#   2. runtime  — slim image with only shared libs and pre-built wheels
# --------------------------------------------------------------------------

# ========================  STAGE 1: builder  ========================
FROM python:3.10-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libvips-dev \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install \
    -r /tmp/requirements.txt gunicorn

# ========================  STAGE 2: runtime  ========================
FROM python:3.10-slim AS runtime

# Runtime-only libs (no gcc, no -dev headers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libvips42 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Application code
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Persistent data directories — mount volumes here in production
RUN mkdir -p /app/data /app/floor-plans /app/project-backups /app/backend/tiles

# Runtime config — SECRET_KEY intentionally omitted (must be set at runtime)
ENV FLASK_ENV=production \
    DATABASE_PATH=/app/data/database.db \
    FLOOR_PLANS_DIR=/app/floor-plans \
    PROJECT_BACKUPS_DIR=/app/project-backups \
    TILES_DIRECTORY=/app/backend/tiles \
    CORS_ORIGINS=http://localhost:5000 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; r = urllib.request.urlopen('http://localhost:5000/'); exit(0 if r.status == 200 else 1)"

WORKDIR /app/backend

# Run migrations then start gunicorn (4 workers, WebSocket-capable via threads)
CMD ["sh", "-c", "python run_migrations.py && gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 'app:create_app(\"production\")'"]
