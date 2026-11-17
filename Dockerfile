# SIDAMA — production image
# Works for Docker Compose, Render, Railway, Fly.io and Hugging Face Spaces:
# start.sh runs migrate → seed demo (only when the database is empty) → gunicorn.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=hf-demo-public-only-key-not-a-secret \
    DJANGO_SECURE_SSL_REDIRECT=0 \
    DJANGO_SECURE_COOKIES=0 \
    SIDAMA_PUBLIC_ONLY=1 \
    SIDAMA_DEMO_AUTO_CONFIRM=1 \
    CELERY_BROKER_URL=disabled

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash sidama \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R sidama:sidama /app \
    && chmod +x /app/start.sh /app/build.sh /app/docker/entrypoint.sh

USER sidama

EXPOSE 8000

CMD ["/app/start.sh"]
