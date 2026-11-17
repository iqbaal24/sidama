"""In-app notifications and Telegram delivery."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Berhasil"
        WARNING = "warning", "Peringatan"
        DANGER = "danger", "Penting"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="pengguna",
                             on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField("judul", max_length=160)
    message = models.CharField("pesan", max_length=500, blank=True)
    url = models.CharField("tautan", max_length=300, blank=True)
    level = models.CharField("level", max_length=20, choices=Level.choices,
                             default=Level.INFO)
    is_read = models.BooleanField("sudah dibaca", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notifikasi"
        verbose_name_plural = "notifikasi"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def tone(self) -> str:
        return self.level
