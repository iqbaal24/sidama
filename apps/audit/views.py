"""Audit log viewer (read-only)."""
from __future__ import annotations

from django.views.generic import DetailView

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.core.mixins import RoleRequiredMixin
from apps.core.views import ColumnListView


class AuditLogListView(ColumnListView):
    model = AuditLog
    allowed_roles = (Role.ADMIN, Role.CHAIR)
    nav = "audit"
    title = "Audit Log"
    subtitle = "Jejak perubahan data — hanya dapat dibaca, tidak dapat diubah."
    headers = ["Waktu", "Pengguna", "Aksi", "Objek", "Catatan"]
    search_fields = ["object_repr", "note", "model_name"]
    row_url_name = "audit:detail"
    empty_text = "Belum ada aktivitas tercatat."
    filters = [
        {"name": "action", "label": "Aksi", "field": "action", "type": "select",
         "options": list(AuditLog.Action.choices)},
        {"name": "user", "label": "Pengguna", "field": "user_id", "type": "select",
         "options": []},
        {"name": "date_from", "label": "Dari", "field": "created_at__date__gte",
         "type": "date"},
        {"name": "date_to", "label": "Sampai", "field": "created_at__date__lte",
         "type": "date"},
    ]

    def get_queryset(self):
        return AuditLog.objects.select_related("user")

    def get_filter_specs(self):
        specs = super().get_filter_specs()
        for spec in specs:
            if spec["name"] == "user":
                spec["options"] = [
                    (str(u.pk), u.display_name)
                    for u in User.objects.filter(is_active=True)
                ]
        return specs

    def get_cells(self, obj):
        tone = {
            AuditLog.Action.CREATE: "success",
            AuditLog.Action.UPDATE: "info",
            AuditLog.Action.DELETE: "danger",
            AuditLog.Action.APPROVE: "success",
            AuditLog.Action.REJECT: "warning",
        }.get(obj.action, "muted")
        return [
            {"text": obj.created_at.strftime("%d/%m/%Y %H:%M"), "muted": True},
            {"text": obj.user.display_name if obj.user else "Sistem"},
            {"text": obj.get_action_display(), "badge": tone},
            {"text": obj.object_repr or obj.model_name,
             "strong": True, "sub": obj.model_name},
            {"text": obj.note or "—", "muted": True},
        ]


class AuditLogDetailView(RoleRequiredMixin, DetailView):
    model = AuditLog
    allowed_roles = (Role.ADMIN, Role.CHAIR)
    template_name = "app/audit_detail.html"
    context_object_name = "log"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav"] = "audit"
        changes = []
        keys = sorted(set(self.object.old_values) | set(self.object.new_values))
        for key in keys:
            old = self.object.old_values.get(key)
            new = self.object.new_values.get(key)
            if old != new:
                changes.append({"field": key, "old": old, "new": new})
        context["changes"] = changes
        return context
