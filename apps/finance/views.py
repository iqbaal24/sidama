"""Finance views: transactions, approval flow, funds, categories, periods."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView, UpdateView

from apps.accounts.models import Role
from apps.audit.services import log_action
from apps.core.mixins import RoleRequiredMixin
from apps.core.models import Setting
from apps.core.utils import month_bounds, month_label
from apps.core.views import ColumnListView, FormPageMixin
from apps.finance.forms import CategoryForm, FundForm, PeriodCloseForm, TransactionForm
from apps.finance.models import Category, Fund, Period, Transaction
from apps.finance.services import fund_balances, month_totals
from apps.notifications.services import notify_roles, notify_user

FINANCE_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER)
VIEW_ROLES = FINANCE_ROLES + (Role.STAFF,)
MANAGE_ROLES = (Role.ADMIN, Role.TREASURER)


class TransactionListView(ColumnListView):
    model = Transaction
    allowed_roles = VIEW_ROLES
    nav = "transactions"
    title = "Transaksi"
    subtitle = "Kas masuk dan keluar masjid"
    headers = ["Tanggal", "Uraian", "Kategori", "Dana", "Nominal", "Status"]
    search_fields = ["description", "pic", "category__name", "fund__name"]
    create_url = reverse_lazy("finance:transaction_create")
    create_roles = FINANCE_ROLES
    create_label = "Catat transaksi"
    empty_text = "Belum ada transaksi pada filter ini."
    row_url_name = "finance:transaction_detail"
    align_right = (4,)
    filters = [
        {"name": "type", "label": "Jenis", "field": "transaction_type", "type": "select",
         "options": [("income", "Pemasukan"), ("expense", "Pengeluaran")]},
        {"name": "status", "label": "Status", "field": "status", "type": "select",
         "options": list(Transaction.Status.choices)},
        {"name": "fund", "label": "Dana", "field": "fund_id", "type": "select",
         "options": []},
        {"name": "category", "label": "Kategori", "field": "category_id", "type": "select",
         "options": []},
        {"name": "date_from", "label": "Dari tanggal", "field": "date__gte", "type": "date"},
        {"name": "date_to", "label": "Sampai tanggal", "field": "date__lte", "type": "date"},
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("category", "fund", "program")

    def get_filter_specs(self):
        specs = super().get_filter_specs()
        for spec in specs:
            if spec["name"] == "fund":
                spec["options"] = [(str(f.pk), f.name) for f in Fund.objects.all()]
            elif spec["name"] == "category":
                spec["options"] = [(str(c.pk), c.name) for c in Category.objects.all()]
        return specs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        context["summary"] = month_totals(today.year, today.month)
        context["summary_label"] = f"{today:%B %Y}".capitalize()
        context["month_pending"] = Transaction.objects.filter(
            status=Transaction.Status.PENDING
        ).count()
        return context

    def get_cells(self, obj):
        status_tone = {
            Transaction.Status.APPROVED: "success",
            Transaction.Status.PENDING: "warning",
            Transaction.Status.REJECTED: "danger",
            Transaction.Status.DRAFT: "muted",
        }.get(obj.status, "muted")
        return [
            {"text": obj.date.strftime("%d/%m/%Y"), "muted": True},
            {"text": obj.description, "strong": True,
             "sub": obj.get_transaction_type_display()},
            {"text": obj.category.name},
            {"text": obj.fund.name, "muted": True},
            {"text": obj.amount, "money": True,
             "tone": "success" if obj.is_income else "ink",
             "sign": "+" if obj.is_income else "−"},
            {"text": obj.get_status_display(), "badge": status_tone},
        ]


class TransactionDetailView(RoleRequiredMixin, DetailView):
    model = Transaction
    template_name = "app/transaction_detail.html"
    allowed_roles = VIEW_ROLES
    context_object_name = "tx"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "category", "fund", "program", "created_by", "approved_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["nav"] = "transactions"
        context["can_edit"] = (
            not self.object.locked and user.role in FINANCE_ROLES
        )
        context["can_delete"] = (
            not self.object.locked and user.role in (Role.ADMIN, Role.TREASURER)
        )
        context["can_approve"] = (
            self.object.is_pending
            and (user.role in (Role.ADMIN, Role.CHAIR) or user.is_superuser)
        )
        context["can_reverse"] = (
            self.object.locked and user.role in FINANCE_ROLES
            and not self.object.reversals.exists()
        )
        context["reversals"] = self.object.reversals.select_related("created_by")
        context["is_pdf"] = bool(
            self.object.receipt and self.object.receipt.name.lower().endswith(".pdf")
        )
        from apps.audit.models import AuditLog

        context["audit_trail"] = AuditLog.objects.filter(
            model_name="finance.Transaction", object_id=str(self.object.pk)
        ).select_related("user")[:12]
        return context


class TransactionCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = FINANCE_ROLES
    nav = "transactions"
    title = "Catat transaksi"
    subtitle = "Pemasukan langsung disetujui; pengeluaran di atas ambang batas menunggu Ketua DKM."
    cancel_url = reverse_lazy("finance:transaction_list")

    def get(self, request):
        form = TransactionForm(user=request.user,
                               initial={"date": timezone.localdate()})
        return render(request, "app/form.html", self.context(form))

    def post(self, request):
        form = TransactionForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            transaction = form.save()
            log_action(request.user, "create", transaction,
                       note="Transaksi dibuat")
            if transaction.is_pending:
                notify_roles(
                    [Role.CHAIR, Role.ADMIN],
                    title="Pengeluaran menunggu persetujuan",
                    message=(f"{transaction.description} sebesar "
                             f"Rp {transaction.amount:,.0f} perlu disetujui."),
                    url=transaction.get_absolute_url(),
                    level="warning",
                )
                messages.warning(
                    request,
                    "Transaksi tersimpan dan menunggu persetujuan Ketua DKM.",
                )
            else:
                messages.success(request, "Transaksi berhasil dicatat.")
            return redirect(transaction)
        return render(request, "app/form.html", self.context(form))


class TransactionUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    allowed_roles = FINANCE_ROLES
    nav = "transactions"
    template_name = "app/form.html"
    title = "Ubah transaksi"
    subtitle = "Setiap perubahan tercatat pada audit log."
    cancel_url = reverse_lazy("finance:transaction_list")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.locked:
            messages.error(request, "Transaksi pada periode tertutup tidak dapat diubah.")
            return redirect(self.object)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Transaksi diperbarui.")
        return super().form_valid(form)


class TransactionDeleteView(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN, Role.TREASURER)

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        if transaction.locked:
            messages.error(request, "Transaksi terkunci tidak dapat dihapus. "
                                    "Gunakan transaksi pembalik.")
            return redirect(transaction)
        description = transaction.description
        log_action(request.user, "delete", transaction,
                   note="Transaksi dihapus", force_snapshot=True)
        transaction.delete()
        messages.success(request, f"Transaksi “{description}” dihapus.")
        return redirect("finance:transaction_list")


class TransactionReverseView(RoleRequiredMixin, View):
    """Create a reversing entry for a locked transaction (correction)."""

    allowed_roles = FINANCE_ROLES

    def post(self, request, pk):
        original = get_object_or_404(Transaction, pk=pk)
        if original.reversals.exists():
            messages.info(request, "Transaksi ini sudah dibalik sebelumnya.")
            return redirect(original)
        reversal = Transaction.objects.create(
            date=timezone.localdate(),
            transaction_type=(Transaction.Type.EXPENSE
                              if original.is_income else Transaction.Type.INCOME),
            fund=original.fund,
            category=original.category,
            amount=original.amount,
            description=f"Pembalik: {original.description}",
            pic=request.user.get_full_name() or request.user.username,
            status=Transaction.Status.APPROVED,
            reversal_of=original,
            created_by=request.user,
        )
        log_action(request.user, "update", original,
                   note=f"Transaksi pembalik #{reversal.pk} dibuat")
        messages.success(request, f"Transaksi pembalik #{reversal.pk} dibuat.")
        return redirect(reversal)


class ApprovalQueueView(ColumnListView):
    model = Transaction
    allowed_roles = (Role.ADMIN, Role.CHAIR)
    nav = "approvals"
    title = "Persetujuan"
    subtitle = "Pengeluaran di atas ambang batas menunggu persetujuan Ketua DKM."
    headers = ["Tanggal", "Uraian", "Dana", "Nominal", "Diajukan oleh", ""]
    empty_text = "Tidak ada pengeluaran yang menunggu persetujuan."
    row_url_name = "finance:transaction_detail"
    template_name = "app/approval_list.html"

    def get_queryset(self):
        return (
            Transaction.objects.filter(status=Transaction.Status.PENDING)
            .select_related("fund", "created_by", "category")
            .order_by("date")
        )

    def get_cells(self, obj):
        return [
            {"text": obj.date.strftime("%d/%m/%Y"), "muted": True},
            {"text": obj.description, "strong": True, "sub": obj.category.name},
            {"text": obj.fund.name, "muted": True},
            {"text": obj.amount, "money": True},
            {"text": obj.created_by.get_full_name() if obj.created_by else "—"},
            {"text": "", "actions": True},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["threshold"] = Setting.get_decimal("approval_threshold", "1000000")
        return context


class TransactionDecisionView(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN, Role.CHAIR)
    approve: bool = True

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        if transaction.status != Transaction.Status.PENDING:
            messages.info(request, "Transaksi ini tidak sedang menunggu persetujuan.")
            return redirect(transaction)
        note = request.POST.get("note", "").strip()
        transaction.status = (
            Transaction.Status.APPROVED if self.approve else Transaction.Status.REJECTED
        )
        transaction.approved_by = request.user
        transaction.approved_at = timezone.now()
        transaction.approval_note = note
        transaction.save()
        log_action(
            request.user,
            "approve" if self.approve else "reject",
            transaction,
            note=note or ("Disetujui" if self.approve else "Ditolak"),
        )
        if transaction.created_by:
            notify_user(
                transaction.created_by,
                title=f"Pengeluaran {'disetujui' if self.approve else 'ditolak'}",
                message=f"{transaction.description} — Rp {transaction.amount:,.0f}",
                url=transaction.get_absolute_url(),
                level="success" if self.approve else "warning",
            )
        messages.success(
            request,
            "Pengeluaran disetujui." if self.approve else "Pengeluaran ditolak.",
        )
        return redirect("finance:approval_queue")


class ApproveTransactionView(TransactionDecisionView):
    approve = True


class RejectTransactionView(TransactionDecisionView):
    approve = False


class FundListView(RoleRequiredMixin, TemplateView):
    template_name = "app/list.html"
    allowed_roles = FINANCE_ROLES
    nav = "funds"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        balances = fund_balances()
        rows = []
        for row in balances:
            fund = row["fund"]
            rows.append({
                "obj": fund,
                "url": reverse("finance:fund_update", args=[fund.pk]),
                "cells": [
                    {"text": fund.name, "strong": True,
                     "sub": fund.description or fund.get_fund_type_display()},
                    {"text": fund.get_fund_type_display(),
                     "badge": {"general": "muted", "zakat": "info",
                               "restricted": "warning"}.get(fund.fund_type, "muted")},
                    {"text": row["income"], "money": True},
                    {"text": row["expense"], "money": True},
                    {"text": row["balance"], "money": True, "strong": True},
                ],
            })
        context.update({
            "title": "Dana",
            "subtitle": "Saldo dipisah per dana: umum, zakat, dan terikat.",
            "headers": ["Nama dana", "Tipe", "Pemasukan", "Pengeluaran", "Saldo"],
            "rows": rows,
            "total_balance": sum(row["balance"] for row in balances),
            "create_url": reverse("finance:fund_create"),
            "create_label": "Tambah dana",
            "can_create": self.request.user.role == Role.ADMIN or self.request.user.is_superuser,
            "empty_text": "Belum ada dana.",
            "nav": self.nav,
            "has_filters": False,
        })
        return context


class FundCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = (Role.ADMIN,)
    nav = "funds"
    title = "Tambah dana"
    subtitle = "Dana baru langsung aktif dan dapat dipakai pada transaksi."
    cancel_url = reverse_lazy("finance:fund_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(FundForm()))

    def post(self, request):
        form = FundForm(request.POST)
        if form.is_valid():
            fund = form.save()
            log_action(request.user, "create", fund, note="Dana dibuat")
            messages.success(request, f"Dana “{fund.name}” ditambahkan.")
            return redirect("finance:fund_list")
        return render(request, "app/form.html", self.context(form))


class FundUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Fund
    form_class = FundForm
    allowed_roles = (Role.ADMIN,)
    nav = "funds"
    template_name = "app/form.html"
    title = "Ubah dana"
    cancel_url = reverse_lazy("finance:fund_list")

    def form_valid(self, form):
        messages.success(self.request, "Dana diperbarui.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("finance:fund_list")


class CategoryListView(ColumnListView):
    model = Category
    allowed_roles = FINANCE_ROLES
    nav = "categories"
    title = "Kategori"
    subtitle = "Kategori pemasukan dan pengeluaran."
    headers = ["Nama kategori", "Tipe", "Keterangan", "Status"]
    create_url = reverse_lazy("finance:category_create")
    create_roles = (Role.ADMIN, Role.TREASURER)
    create_label = "Tambah kategori"
    row_url_name = "finance:category_update"
    search_fields = ["name"]

    def get_cells(self, obj):
        return [
            {"text": obj.name, "strong": True},
            {"text": obj.get_category_type_display(),
             "badge": "success" if obj.category_type == "income" else "warning"},
            {"text": obj.description or "—", "muted": True},
            {"text": "Aktif" if obj.is_active else "Nonaktif",
             "badge": "success" if obj.is_active else "muted"},
        ]


class CategoryCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = (Role.ADMIN, Role.TREASURER)
    nav = "categories"
    title = "Tambah kategori"
    cancel_url = reverse_lazy("finance:category_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(CategoryForm()))

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            log_action(request.user, "create", category, note="Kategori dibuat")
            messages.success(request, f"Kategori “{category.name}” ditambahkan.")
            return redirect("finance:category_list")
        return render(request, "app/form.html", self.context(form))


class CategoryUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    allowed_roles = (Role.ADMIN, Role.TREASURER)
    nav = "categories"
    template_name = "app/form.html"
    title = "Ubah kategori"
    cancel_url = reverse_lazy("finance:category_list")

    def get_success_url(self):
        return reverse("finance:category_list")

    def form_valid(self, form):
        messages.success(self.request, "Kategori diperbarui.")
        return super().form_valid(form)


class PeriodListView(RoleRequiredMixin, TemplateView):
    template_name = "app/period_list.html"
    allowed_roles = FINANCE_ROLES
    nav = "periods"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        periods = list(Period.objects.select_related("closed_by"))
        existing = {(p.year, p.month): p for p in periods}
        rows = []
        year, month = today.year, today.month
        for offset in range(0, 14):
            index = year * 12 + (month - 1) - offset
            y, m = index // 12, index % 12 + 1
            period = existing.get((y, m))
            start, end = month_bounds(y, m)
            totals = month_totals(y, m)
            rows.append({
                "year": y,
                "month": m,
                "period": period,
                "closed": bool(period and period.is_closed),
                "label": month_label(y, m),
                "income": totals["income"],
                "expense": totals["expense"],
                "count": Transaction.objects.filter(date__gte=start, date__lte=end).count(),
            })
        context.update({
            "title": "Periode & Tutup Buku",
            "subtitle": "Menutup periode mengunci seluruh transaksi di dalamnya.",
            "rows": rows,
            "nav": self.nav,
            "form": kwargs.get("form") or PeriodCloseForm(),
            "today": today,
        })
        return context


class ClosePeriodView(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN, Role.TREASURER)

    def post(self, request):
        form = PeriodCloseForm(request.POST)
        year = int(request.POST.get("year") or timezone.localdate().year)
        month = int(request.POST.get("month") or timezone.localdate().month)
        if not form.is_valid():
            messages.error(request, "Periksa kembali isian penutupan periode.")
            return redirect("finance:period_list")
        period, _ = Period.objects.get_or_create(year=year, month=month)
        if period.is_closed:
            messages.info(request, f"Periode {period.label} sudah ditutup.")
            return redirect("finance:period_list")
        start, end = month_bounds(year, month)
        locked = Transaction.objects.filter(date__gte=start, date__lte=end).update(locked=True)
        period.is_closed = True
        period.closed_at = timezone.now()
        period.closed_by = request.user
        period.note = form.cleaned_data.get("note", "")
        period.save()
        log_action(request.user, "update", period,
                   note=f"Periode {period.label} ditutup; {locked} transaksi dikunci")
        messages.success(
            request,
            f"Periode {period.label} ditutup. {locked} transaksi dikunci.",
        )
        return redirect("finance:period_list")


class ReopenPeriodView(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN,)

    def post(self, request, pk):
        period = get_object_or_404(Period, pk=pk)
        if not period.is_closed:
            messages.info(request, "Periode ini belum ditutup.")
            return redirect("finance:period_list")
        start, end = month_bounds(period.year, period.month)
        Transaction.objects.filter(date__gte=start, date__lte=end).update(locked=False)
        period.is_closed = False
        period.closed_at = None
        period.closed_by = None
        period.save()
        log_action(request.user, "update", period,
                   note=f"Periode {period.label} dibuka kembali")
        messages.warning(request, f"Periode {period.label} dibuka kembali oleh admin.")
        return redirect("finance:period_list")
