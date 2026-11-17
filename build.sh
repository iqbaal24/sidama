#!/usr/bin/env bash
# Build step for managed platforms (Render, Railway, Fly).
# Installs nothing (the platform installs requirements.txt), then prepares the DB,
# static files, and demo data so a fresh deploy is immediately usable.
set -euo pipefail

echo "→ migrate"
python manage.py migrate --noinput

echo "→ collectstatic"
python manage.py collectstatic --noinput

echo "→ seed demo data (skipped if the database already has users)"
python manage.py seed_demo || echo "seed_demo dilewati"

echo "→ build selesai"
