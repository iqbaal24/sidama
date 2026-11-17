"""Shared settings stored in the database (editable by the admin)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("dibuat pada", auto_now_add=True)
    updated_at = models.DateTimeField("diperbarui pada", auto_now=True)

    class Meta:
        abstract = True


class Setting(models.Model):
    key = models.CharField("kunci", max_length=80, unique=True)
    value = models.CharField("nilai", max_length=255, blank=True)
    label = models.CharField("label", max_length=120, blank=True)
    group = models.CharField("grup", max_length=40, default="umum")

    class Meta:
        verbose_name = "pengaturan"
        verbose_name_plural = "pengaturan"
        ordering = ["group", "key"]

    def __str__(self) -> str:
        return f"{self.key}={self.value}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Setting._cache = {}

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        Setting._cache = {}

    _cache: dict[str, str] = {}

    @classmethod
    def get(cls, key: str, default: str | None = None) -> str | None:
        if key not in cls._cache:
            cls._cache[key] = (
                cls.objects.filter(key=key).values_list("value", flat=True).first()
            )
        value = cls._cache[key]
        if value is None or value == "":
            return settings.SIDAMA_DEFAULTS.get(key, default)
        return value

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        try:
            return int(Decimal(str(cls.get(key, default))))
        except (InvalidOperation, TypeError, ValueError):
            return default

    @classmethod
    def get_decimal(cls, key: str, default: str = "0") -> Decimal:
        try:
            return Decimal(str(cls.get(key, default)))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(default)

    @classmethod
    def set(cls, key: str, value, *, label: str = "", group: str = "umum") -> "Setting":
        obj, _ = cls.objects.update_or_create(
            key=key, defaults={"value": str(value), "label": label, "group": group}
        )
        return obj
