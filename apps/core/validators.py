"""Upload validation shared by finance and program receipts."""
from __future__ import annotations

from django.core.exceptions import ValidationError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def validate_upload_size(file):
    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Ukuran berkas maksimal 5 MB.")


def validate_upload_type(file):
    name = getattr(file, "name", "") or ""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Format berkas harus JPG, PNG, atau PDF.")
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Tipe berkas tidak dikenali sebagai gambar atau PDF.")
