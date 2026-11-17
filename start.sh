#!/usr/bin/env bash
# Start command for managed platforms (Render, Railway, Fly, Hugging Face Spaces,
# Docker): prepare static files, the SQLite database, demo data, then gunicorn.
#
# collectstatic MUST run here (not only at build time): with DEBUG=0 Django uses
# CompressedManifestStaticFilesStorage, and a missing manifest makes every page 500.
set -euo pipefail

echo "→ collectstatic"
python manage.py collectstatic --noinput --clear

echo "→ migrate"
python manage.py migrate --noinput

echo "→ seed demo data (dilewati bila database sudah berisi)"
python manage.py seed_demo || echo "seed_demo dilewati"

echo "→ start gunicorn"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --access-logfile -
