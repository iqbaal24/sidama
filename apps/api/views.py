"""REST API views (token authenticated, role aware)."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import IsApprover, IsDataManager, IsFinance
from apps.api.serializers import (
    AssetSerializer,
    AuditLogSerializer,
    CategorySerializer,
    DonationDecisionSerializer,
    DonationSerializer,
    FundSerializer,
    MeatDistributionSerializer,
    MustahikSerializer,
    MuzakkiSerializer,
    ProgramDonateSerializer,
    ProgramSerializer,
    QurbanRegistrationSerializer,
    ReportGenerateSerializer,
    ReportSerializer,
    TransactionSerializer,
    ZakatDistributionSerializer,
    ZakatReceiptSerializer,
)
from apps.assets.models import Asset
from apps.audit.models import AuditLog
from apps.core.models import Setting
from apps.core.utils import month_label
from apps.finance.models import Category, Fund, Transaction
from apps.finance.services import cash_position, fund_balances, month_totals, monthly_series
from apps.forecasting.services import cashflow_forecast
from apps.programs.models import Donation, Program
from apps.programs.services import confirm_donation, reject_donation
from apps.qurban.models import MeatDistribution, QurbanRegistration
from apps.reports.generator import generate_report
from apps.reports.models import Report
from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt
from apps.zakat.services import calculate_zakat


@extend_schema(tags=["auth"])
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("username") or request.data.get("email") or ""
        password = request.data.get("password") or ""
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            return Response({"detail": "Kredensial tidak valid."},
                            status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": {
                "id": user.pk,
                "username": user.username,
                "name": user.display_name,
                "email": user.email,
                "role": user.role,
                "role_label": user.role_label,
            },
        })


@extend_schema(tags=["auth"])
class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response({
            "id": user.pk,
            "username": user.username,
            "name": user.display_name,
            "email": user.email,
            "role": user.role,
            "role_label": user.role_label,
        })


@extend_schema(tags=["finance"])
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["transaction_type", "status", "fund", "category"]

    def get_queryset(self):
        queryset = Transaction.objects.select_related(
            "fund", "category", "program", "created_by"
        )
        if self.request.user.role not in ("admin", "chair", "treasurer", "staff"):
            queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def perform_destroy(self, instance):
        if instance.locked:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Transaksi terkunci tidak dapat dihapus.")
        instance.delete()

    @extend_schema(tags=["finance"], request=None)
    @action(detail=True, methods=["post"], permission_classes=[IsApprover])
    def approve(self, request, pk=None):
        transaction = self.get_object()
        if transaction.status != Transaction.Status.PENDING:
            return Response({"detail": "Transaksi tidak menunggu persetujuan."},
                            status=status.HTTP_400_BAD_REQUEST)
        transaction.status = Transaction.Status.APPROVED
        transaction.approved_by = request.user
        transaction.approved_at = timezone.now()
        transaction.approval_note = request.data.get("note", "")
        transaction.save()
        return Response(self.get_serializer(transaction).data)

    @extend_schema(tags=["finance"], request=DonationDecisionSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsApprover])
    def reject(self, request, pk=None):
        transaction = self.get_object()
        if transaction.status != Transaction.Status.PENDING:
            return Response({"detail": "Transaksi tidak menunggu persetujuan."},
                            status=status.HTTP_400_BAD_REQUEST)
        transaction.status = Transaction.Status.REJECTED
        transaction.approved_by = request.user
        transaction.approved_at = timezone.now()
        transaction.approval_note = request.data.get("note", "")
        transaction.save()
        return Response(self.get_serializer(transaction).data)


@extend_schema(tags=["finance"])
class FundViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Fund.objects.all()
    serializer_class = FundSerializer
    permission_classes = [IsFinance]

    @extend_schema(tags=["finance"])
    @action(detail=False, methods=["get"], url_path="balance")
    def balance(self, request):
        rows = fund_balances()
        return Response({
            "total_balance": sum(row["balance"] for row in rows),
            "funds": [
                {
                    "id": row["fund"].pk,
                    "name": row["fund"].name,
                    "type": row["fund"].fund_type,
                    "income": row["income"],
                    "expense": row["expense"],
                    "balance": row["balance"],
                }
                for row in rows
            ],
        })


@extend_schema(tags=["finance"])
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsFinance]


class ProgramViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramSerializer
    lookup_field = "slug"

    def get_queryset(self):
        queryset = Program.objects.all()
        user = self.request.user
        if not (user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "chair", "treasurer", "staff")
        )):
            queryset = queryset.filter(is_published=True)
        return queryset.order_by("-created_at")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        if self.action == "donate":
            return [AllowAny()]
        return [IsDataManager()]

    @extend_schema(tags=["programs"], request=ProgramDonateSerializer,
                   responses={201: DonationSerializer})
    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def donate(self, request, slug=None):
        program = self.get_object()
        if not program.is_open:
            return Response({"detail": "Program tidak menerima donasi."},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = ProgramDonateSerializer(
            data=request.data, context={"request": request, "program": program}
        )
        serializer.is_valid(raise_exception=True)
        donation = serializer.save()
        return Response(DonationSerializer(donation, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["programs"])
class DonationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    serializer_class = DonationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Donation.objects.select_related("program")
        if user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "chair", "treasurer", "staff")
        ):
            return queryset
        if user.is_authenticated:
            return queryset.filter(donor_user=user)
        return queryset.none()

    def get_permissions(self):
        if self.action in {"confirm", "reject"}:
            return [IsFinance()]
        return [IsAuthenticated()]

    @extend_schema(tags=["programs"], request=DonationDecisionSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsFinance])
    def confirm(self, request, pk=None):
        donation = self.get_object()
        confirm_donation(donation, request.user)
        return Response(DonationSerializer(donation, context={"request": request}).data)

    @extend_schema(tags=["programs"], request=DonationDecisionSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsFinance])
    def reject(self, request, pk=None):
        donation = self.get_object()
        reject_donation(donation, request.user, request.data.get("note", ""))
        return Response(DonationSerializer(donation, context={"request": request}).data)


class ZakatReceiptViewSet(viewsets.ModelViewSet):
    queryset = ZakatReceipt.objects.select_related("muzakki")
    serializer_class = ZakatReceiptSerializer
    permission_classes = [IsFinance]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == "staff" or user.role == "chair":
            return queryset
        return queryset


class MuzakkiViewSet(viewsets.ModelViewSet):
    queryset = Muzakki.objects.all()
    serializer_class = MuzakkiSerializer
    permission_classes = [IsDataManager]


class MustahikViewSet(viewsets.ModelViewSet):
    queryset = Mustahik.objects.all()
    serializer_class = MustahikSerializer
    permission_classes = [IsDataManager]


class ZakatDistributionViewSet(viewsets.ModelViewSet):
    queryset = ZakatDistribution.objects.select_related("mustahik")
    serializer_class = ZakatDistributionSerializer
    permission_classes = [IsFinance]


@extend_schema(tags=["zakat"])
class ZakatCalculateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            zakat_type = request.query_params.get("type", "mal")
            result = calculate_zakat(
                zakat_type=zakat_type,
                assets=request.query_params.get("assets", 0),
                debts=request.query_params.get("debts", 0),
                monthly_income=request.query_params.get("income", 0),
                dependents=request.query_params.get("dependents", 1),
            )
        except Exception:  # noqa: BLE001 - invalid query values
            return Response({"detail": "Parameter tidak valid."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({
            key: (str(value) if hasattr(value, "quantize") else value)
            for key, value in result.items()
        })


class QurbanRegistrationViewSet(viewsets.ModelViewSet):
    queryset = QurbanRegistration.objects.all()
    serializer_class = QurbanRegistrationSerializer
    permission_classes = [IsDataManager]


class MeatDistributionViewSet(viewsets.ModelViewSet):
    queryset = MeatDistribution.objects.select_related("registration")
    serializer_class = MeatDistributionSerializer
    permission_classes = [IsDataManager]


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.prefetch_related("logs")
    serializer_class = AssetSerializer
    permission_classes = [IsDataManager]

    def perform_create(self, serializer):
        serializer.save()


@extend_schema(tags=["reports"])
class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsFinance]

    @extend_schema(tags=["reports"], request=ReportGenerateSerializer)
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        serializer = ReportGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        report, _ = Report.objects.get_or_create(
            report_type=data["report_type"],
            period_year=data["period_year"],
            period_month=data.get("period_month"),
            defaults={"created_by": request.user},
        )
        generate_report(report)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["public"])
class PublicSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.localdate()
        return Response({
            "mosque": {
                "name": Setting.get("mosque_name"),
                "city": Setting.get("mosque_city"),
                "address": Setting.get("mosque_address"),
            },
            "total_balance": cash_position(),
            "month": {
                "label": month_label(today.year, today.month),
                **{key: str(value) for key, value in
                   month_totals(today.year, today.month).items()},
            },
            "series": monthly_series(12),
            "funds": [
                {"name": row["fund"].name, "type": row["fund"].fund_type,
                 "balance": row["balance"]}
                for row in fund_balances()
            ],
            "programs": ProgramSerializer(
                Program.objects.filter(is_published=True)[:6], many=True
            ).data,
        })


@extend_schema(tags=["public"])
class ForecastView(APIView):
    permission_classes = [IsFinance]

    def get(self, request):
        forecast = cashflow_forecast()
        return Response({
            "balance": forecast["balance"],
            "avg_income": forecast["avg_income"],
            "avg_expense": forecast["avg_expense"],
            "projected_balance": forecast["projected_balance"],
            "runway_months": forecast["runway_months"],
            "status": forecast["status"],
            "months": forecast["months"],
        })


@extend_schema(tags=["public"])
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = [IsApprover]
