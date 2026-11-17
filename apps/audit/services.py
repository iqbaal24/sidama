"""Audit log helpers: serialisation, signals and explicit logging."""
from __future__ import annotations

import json
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Model
from django.db.models.fields.files import FieldFile

from apps.audit.middleware import get_current_ip, get_current_user
from apps.audit.models import AuditLog

# Fields that should never appear in the audit trail.
EXCLUDED_FIELDS = {
    "password", "last_login", "updated_at", "created_at",
}


def _serialise(value):
    if isinstance(value, FieldFile):
        return value.name or ""
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Model):
        return value.pk
    if isinstance(value, (list, dict)):
        return json.loads(json.dumps(value, default=str))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def snapshot(instance: Model) -> dict:
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in EXCLUDED_FIELDS:
            continue
        try:
            data[field.name] = _serialise(getattr(instance, field.name))
        except Exception:  # noqa: BLE001 - a single bad field must not break saving
            continue
    return data


def log_action(user, action: str, instance: Model, *, note: str = "",
               old_values: dict | None = None, new_values: dict | None = None,
               force_snapshot: bool = False) -> AuditLog | None:
    """Write an audit entry. Signals call this automatically for tracked models."""
    if user is not None and not getattr(user, "is_authenticated", False):
        user = None
    if old_values is None and new_values is None and not force_snapshot:
        new_values = snapshot(instance)
    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=instance._meta.label,
        object_id=str(instance.pk or ""),
        object_repr=str(instance)[:255],
        old_values=old_values or {},
        new_values=new_values or {},
        note=note[:255],
        ip_address=get_current_ip(),
    )


TRACKED_MODELS = [
    "accounts.User",
    "finance.Fund",
    "finance.Category",
    "finance.Period",
    "finance.Transaction",
    "programs.Program",
    "programs.Donation",
    "zakat.Muzakki",
    "zakat.ZakatReceipt",
    "zakat.Mustahik",
    "zakat.ZakatDistribution",
    "qurban.QurbanRegistration",
    "qurban.MeatDistribution",
    "assets.Asset",
    "assets.AssetLog",
    "core.Setting",
]


def _connect(sender):
    from django.db.models.signals import post_delete, post_save, pre_save

    def pre_save_handler(instance, **kwargs):
        if not instance.pk:
            return
        try:
            previous = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return
        instance._audit_old = snapshot(previous)

    def post_save_handler(instance, created, **kwargs):
        if created:
            log_action(get_current_user(), AuditLog.Action.CREATE, instance,
                       new_values=snapshot(instance))
            return
        old = getattr(instance, "_audit_old", None)
        if old is None:
            return
        new = snapshot(instance)
        old_values = {}
        new_values = {}
        for key, value in new.items():
            if old.get(key) != value:
                old_values[key] = old.get(key)
                new_values[key] = value
        if not old_values:
            return
        log_action(get_current_user(), AuditLog.Action.UPDATE, instance,
                   old_values=old_values, new_values=new_values)

    def post_delete_handler(instance, **kwargs):
        log_action(get_current_user(), AuditLog.Action.DELETE, instance,
                   old_values=snapshot(instance), force_snapshot=True)

    pre_save.connect(pre_save_handler, sender=sender, weak=False,
                     dispatch_uid=f"audit-pre-save-{sender._meta.label}")
    post_save.connect(post_save_handler, sender=sender, weak=False,
                      dispatch_uid=f"audit-post-save-{sender._meta.label}")
    post_delete.connect(post_delete_handler, sender=sender, weak=False,
                        dispatch_uid=f"audit-post-delete-{sender._meta.label}")


def register_signals():
    from django.apps import apps

    for label in TRACKED_MODELS:
        try:
            model = apps.get_model(label)
        except LookupError:
            continue
        _connect(model)
