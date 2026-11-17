"""Celery tasks for report generation and monthly scheduling."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.notifications.services import send_telegram_async
from apps.reports.generator import generate_report
from apps.reports.models import Report

logger = logging.getLogger("sidama.reports")


@shared_task(name="reports.generate")
def generate_report_task(report_id: int) -> int:
    report = Report.objects.get(pk=report_id)
    generate_report(report)
    logger.info("Laporan %s dibuat", report)
    return report.pk


@shared_task(name="reports.monthly")
def create_monthly_report(year: int | None = None, month: int | None = None) -> int | None:
    """Create and render the report for the previous month."""
    today = timezone.localdate()
    if year is None or month is None:
        first = today.replace(day=1)
        previous = first - timezone.timedelta(days=1)
        year, month = previous.year, previous.month
    report, created = Report.objects.get_or_create(
        report_type=Report.Type.MONTHLY,
        period_year=year,
        period_month=month,
        defaults={"status": Report.Status.DRAFT},
    )
    if not created and report.generated_at:
        return report.pk
    generate_report(report)
    send_telegram_async(
        f"📊 Laporan keuangan {report.period_label} sudah dibuat dan menunggu penerbitan."
    )
    return report.pk


@shared_task(name="reports.annual")
def create_annual_report(year: int | None = None) -> int | None:
    year = year or timezone.localdate().year
    report, _ = Report.objects.get_or_create(
        report_type=Report.Type.ANNUAL,
        period_year=year,
        period_month=None,
        defaults={"status": Report.Status.DRAFT},
    )
    generate_report(report)
    return report.pk
