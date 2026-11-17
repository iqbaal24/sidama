"""Immutable audit trail for changes to important records."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Membuat"
        UPDATE = "update", "Mengubah"
        DELETE = "delete", "Menghapus"
        APPROVE = "approve", "Menyetujui"
        REJECT = "reject", "Menolak"
        CONFIRM = "confirm", "Mengonfirmasi"
        PUBLISH = "publish", "Menerbitkan"
        LOGIN = "login", "Masuk"
        LOGOUT = "logout", "Keluar"
        GENERATE = "generate", "Membuat laporan"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="pengguna",
                             null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="audit_logs")
    action = models.CharField("aksi", max_length=20, choices=Action.choices)
    model_name = models.CharField("model", max_length=80)
    object_id = models.CharField("id objek", max_length=40, blank=True)
    object_repr = models.CharField("objek", max_length=255, blank=True)
    old_values = models.JSONField("nilai lama", default=dict, blank=True)
    new_values = models.JSONField("nilai baru", default=dict, blank=True)
    note = models.CharField("catatan", max_length=255, blank=True)
    ip_address = models.GenericIPAddressField("alamat IP", null=True, blank=True)
    created_at = models.DateTimeField("waktu", auto_now_add=True)

    class Meta:
        verbose_name = "audit log"
        verbose_name_plural = "audit log"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} {self.model_name} #{self.object_id}"
