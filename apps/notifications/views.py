"""Notification inbox."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.notifications.models import Notification


class NotificationListView(LoginRequiredMixin, TemplateView):
    template_name = "app/notifications.html"
    nav = "notifications"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "nav": self.nav,
            "title": "Notifikasi",
            "notifications": Notification.objects.filter(user=self.request.user),
        })
        return context


class NotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return redirect(notification.url or "notifications:list")


class NotificationReadAllView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "Semua notifikasi ditandai sudah dibaca.")
        return redirect("notifications:list")
