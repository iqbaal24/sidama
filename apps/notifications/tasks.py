"""Celery tasks for notifications."""
from celery import shared_task

from apps.notifications.services import send_telegram


@shared_task(name="notifications.send_telegram")
def send_telegram_task(text: str) -> bool:
    return send_telegram(text)
