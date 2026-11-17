#!/usr/bin/env bash
# Start command for managed platforms: prepare the SQLite database on every boot,
# seed demo data when it is empty, then hand over to gunicorn.
set -euo pipefail

echo "→ migrate"
python manage.py migrate --noinput

echo "→ seed demo data (dilewati bila database sudah berisi)"
python manage.py seed_demo || echo "seed_demo dilewati"

echo "→ start gunicorn"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile -
