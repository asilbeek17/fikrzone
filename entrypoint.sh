#!/usr/bin/env bash
# Runs as root → initializes volumes → drops to appuser via gosu
set -euo pipefail

# ── Volume directory initialization (must run as root) ────────────────────────
echo "[entrypoint] Initializing volume directories..."
mkdir -p \
    /app/data \
    /app/staticfiles \
    /app/media/covers \
    /app/media/blocks/images \
    /app/media/blocks/videos \
    /app/media/blocks/audio

# Give appuser (UID 1000) ownership of all writable mounts
chown -R 1000:1000 /app/data /app/staticfiles /app/media

# ── Drop privileges to appuser for all app operations ─────────────────────────
echo "[entrypoint] Dropping to appuser (UID 1000)..."

exec gosu appuser bash -s <<'APP_CMD'
set -euo pipefail

echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Starting Gunicorn (workers=${GUNICORN_WORKERS:-4})..."
exec gunicorn editorial.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-4}" \
  --worker-class sync \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --log-level info \
  --access-logfile - \
  --error-logfile -
APP_CMD
