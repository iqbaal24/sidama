"""Report generation, publishing and downloads."""
from __future__ import annotations

import shutil
import tempfile

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.reports.generator import generate_report
from apps.reports.models import Report
from tests.base import BaseTestCase

MEDIA_ROOT = tempfile.mkdtemp(prefix="sidama-test-media-")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ReportTests(BaseTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        today = timezone.localdate()
        self.make_transaction(amount="4000000", date=today.replace(day=1))
        self.make_transaction(amount="1500000", transaction_type="expense",
                              date=today.replace(day=1))

    def test_generate_report_creates_pdf_and_excel(self):
        report = Report.objects.create(
            report_type=Report.Type.MONTHLY,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
            created_by=self.treasurer,
        )
        generate_report(report)
        report.refresh_from_db()
        self.assertTrue(report.pdf_file.name.endswith(".pdf"))
        self.assertTrue(report.xlsx_file.name.endswith(".xlsx"))
        self.assertIsNotNone(report.generated_at)

    def test_treasurer_generates_report_via_view(self):
        self.client.force_login(self.treasurer)
        today = timezone.localdate()
        response = self.client.post(reverse("reports:generate"), {
            "report_type": Report.Type.MONTHLY,
            "period_year": today.year,
            "period_month": str(today.month),
        })
        self.assertRedirects(response, reverse("reports:list"))
        report = Report.objects.get(report_type=Report.Type.MONTHLY,
                                    period_year=today.year,
                                    period_month=today.month)
        self.assertTrue(report.pdf_file)
        self.assertEqual(report.status, Report.Status.DRAFT)

    def test_published_report_is_public_and_downloadable(self):
        report = Report.objects.create(
            report_type=Report.Type.MONTHLY,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
        )
        generate_report(report)
        self.client.force_login(self.chair)
        response = self.client.post(reverse("reports:publish", args=[report.pk]))
        self.assertRedirects(response, reverse("reports:list"))
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.PUBLISHED)

        self.client.logout()
        public_list = self.client.get(reverse("public:reports"))
        self.assertContains(public_list, report.period_label)
        download = self.client.get(
            reverse("public:report_download", args=[report.pk, "pdf"])
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")

    def test_draft_report_cannot_be_downloaded_publicly(self):
        report = Report.objects.create(
            report_type=Report.Type.MONTHLY,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
        )
        generate_report(report)
        response = self.client.get(
            reverse("public:report_download", args=[report.pk, "pdf"])
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_cannot_generate_reports(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("reports:generate"))
        self.assertEqual(response.status_code, 403)
