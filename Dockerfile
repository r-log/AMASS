# --------------------------------------------------------------------------
# Electrician Log MVP — single-container image
# Flask serves the API + frontend static files on port 5000.
# --------------------------------------------------------------------------

FROM python:3.10-slim AS base

# System deps for pyvips (image tiling) and pdf2image (poppler)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libvips-dev \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --------------------------------------------------------------------------
# Python dependencies (cached layer — only re-runs when requirements change)
# --------------------------------------------------------------------------
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt gunicorn

# --------------------------------------------------------------------------
# Application code
# --------------------------------------------------------------------------
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Persistent data directories — mount volumes here in production
RUN mkdir -p /app/data /app/floor-plans /app/project-backups /app/backend/tiles

# --------------------------------------------------------------------------
# Runtime config
# --------------------------------------------------------------------------
ENV FLASK_ENV=production \
    SECRET_KEY="" \
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
