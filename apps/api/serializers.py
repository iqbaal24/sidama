"""Serializers for the public REST API."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.assets.models import Asset, AssetLog
from apps.audit.models import AuditLog
from apps.finance.models import Category, Fund, Transaction
from apps.finance.services import fund_balance
from apps.programs.models import Donation, Program
from apps.programs.services import create_donation
from apps.qurban.models import MeatDistribution, QurbanRegistration
from apps.reports.models import Report
from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt
from apps.zakat.services import record_distribution, record_receipt


class FundSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Fund
        fields = ["id", "name", "code", "fund_type", "description", "is_active",
                  "balance"]

    def get_balance(self, obj):
        return fund_balance(obj)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "category_type", "description", "is_active"]


class TransactionSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    program_title = serializers.CharField(source="program.title", read_only=True,
                                          default=None)

    class Meta:
        model = Transaction
        fields = [
            "id", "date", "transaction_type", "fund", "fund_name", "category",
            "category_name", "amount", "description", "pic", "receipt", "status",
            "locked", "program", "program_title", "created_by", "approved_by",
            "approved_at", "approval_note", "created_at",
        ]
        read_only_fields = ["status", "locked", "created_by", "approved_by",
                            "approved_at", "approval_note"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        if instance and instance.locked:
            raise serializers.ValidationError(
                "Transaksi berada pada periode tertutup dan tidak dapat diubah."
            )
        category = attrs.get("category") or getattr(instance, "category", None)
        transaction_type = attrs.get("transaction_type") or getattr(
            instance, "transaction_type", None
        )
        if category and transaction_type and category.category_type != transaction_type:
            raise serializers.ValidationError(
                {"category": "Kategori tidak sesuai dengan jenis transaksi."}
            )
        amount = attrs.get("amount")
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Nominal harus lebih dari 0."})
        return attrs

    def create(self, validated_data):
        from apps.finance.services import default_status

        request = self.context.get("request")
        user = getattr(request, "user", None)
        validated_data["created_by"] = user if getattr(user, "is_authenticated", False) else None
        validated_data["status"] = default_status(
            validated_data["transaction_type"], validated_data["amount"]
        )
        return super().create(validated_data)


class ProgramSerializer(serializers.ModelSerializer):
    collected = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    donor_count = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = ["id", "title", "slug", "description", "target_amount",
                  "start_date", "end_date", "image", "status", "is_published",
                  "collected", "progress", "donor_count", "created_at"]
        read_only_fields = ["slug"]

    def get_collected(self, obj):
        return obj.collected

    def get_progress(self, obj):
        return obj.progress

    def get_donor_count(self, obj):
        return obj.donor_count


class DonationSerializer(serializers.ModelSerializer):
    program_title = serializers.CharField(source="program.title", read_only=True)
    donor_display = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = ["id", "code", "program", "program_title", "donor_name",
                  "donor_display", "is_anonymous", "amount", "method", "message",
                  "status", "created_at", "confirmed_at"]
        read_only_fields = ["code", "status", "confirmed_at"]

    def get_donor_display(self, obj):
        return obj.display_name

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        privileged = bool(user and user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "chair", "treasurer", "staff")
        ))
        if not privileged:
            data.pop("donor_name", None)
        return data


class ProgramDonateSerializer(serializers.Serializer):
    donor_name = serializers.CharField(max_length=120)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("10000"))
    method = serializers.ChoiceField(choices=Donation.Method.choices,
                                     default=Donation.Method.QRIS)
    message = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_anonymous = serializers.BooleanField(default=False)
    contact = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def create(self, validated_data):
        program = self.context["program"]
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return create_donation(
            program=program,
            donor_user=user if getattr(user, "is_authenticated", False) else None,
            **validated_data,
        )


class DonationDecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class MuzakkiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Muzakki
        fields = ["id", "name", "phone", "address", "note"]


class ZakatReceiptSerializer(serializers.ModelSerializer):
    payer_name = serializers.CharField(read_only=True)
    muzakki_name = serializers.CharField(read_only=True)

    class Meta:
        model = ZakatReceipt
        fields = ["id", "number", "muzakki", "muzakki_name", "payer_name",
                  "zakat_type", "amount", "date", "note", "transaction",
                  "created_at"]
        read_only_fields = ["number", "transaction"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        receipt = ZakatReceipt.objects.create(**validated_data)
        return record_receipt(receipt, user)


class MustahikSerializer(serializers.ModelSerializer):
    total_received = serializers.DecimalField(max_digits=14, decimal_places=2,
                                              read_only=True)

    class Meta:
        model = Mustahik
        fields = ["id", "name", "asnaf", "address", "phone", "is_verified",
                  "note", "total_received"]


class ZakatDistributionSerializer(serializers.ModelSerializer):
    mustahik_name = serializers.CharField(source="mustahik.name", read_only=True)

    class Meta:
        model = ZakatDistribution
        fields = ["id", "mustahik", "mustahik_name", "amount", "item_description",
                  "date", "note", "transaction", "created_at"]
        read_only_fields = ["transaction"]

    def validate_mustahik(self, mustahik):
        if not mustahik.is_verified:
            raise serializers.ValidationError("Mustahik belum terverifikasi.")
        return mustahik

    def create(self, validated_data):
        request = self.context.get("request")
        distribution = ZakatDistribution.objects.create(**validated_data)
        return record_distribution(distribution, request.user)


class QurbanRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QurbanRegistration
        fields = ["id", "year", "name", "phone", "animal_type", "share_count",
                  "amount", "payment_status", "note", "created_at"]


class MeatDistributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeatDistribution
        fields = ["id", "registration", "recipient_name", "weight_kg",
                  "coupon_code", "is_received", "received_at", "note"]
        read_only_fields = ["coupon_code", "received_at"]


class AssetLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetLog
        fields = ["id", "log_type", "note", "date", "created_by"]
        read_only_fields = ["created_by"]


class AssetSerializer(serializers.ModelSerializer):
    logs = AssetLogSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = ["id", "name", "category", "quantity", "condition", "location",
                  "acquired_date", "value", "note", "logs", "created_at"]


class ReportSerializer(serializers.ModelSerializer):
    period_label = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ["id", "report_type", "period_year", "period_month",
                  "period_label", "status", "pdf_file", "xlsx_file",
                  "generated_at", "published_at", "note"]
        read_only_fields = ["status", "generated_at", "published_at"]


class ReportGenerateSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=Report.Type.choices,
                                          default=Report.Type.MONTHLY)
    period_year = serializers.IntegerField(min_value=2020, max_value=2100)
    period_month = serializers.IntegerField(min_value=1, max_value=12, required=False,
                                            allow_null=True)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["report_type"] == Report.Type.MONTHLY and not attrs.get("period_month"):
            raise serializers.ValidationError(
                {"period_month": "Laporan bulanan membutuhkan bulan."}
            )
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True,
                                      default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "created_at", "user", "user_name", "action", "model_name",
                  "object_id", "object_repr", "old_values", "new_values", "note",
                  "ip_address"]
        read_only_fields = fields
