#!/usr/bin/env bash
# Build step for managed platforms (Render, Railway, Fly).
# Only collects static files: migrations and seeding happen at boot in start.sh
# so a fresh instance always has a working SQLite database.
set -euo pipefail

echo "→ collectstatic"
python manage.py collectstatic --noinput

echo "→ build selesai"
