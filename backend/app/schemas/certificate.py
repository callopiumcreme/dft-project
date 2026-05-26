from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

CertStatus = Literal["active", "expired", "revoked", "placeholder"]


class CertificateBase(BaseModel):
    cert_number: str
    scheme: str = "ISCC EU"
    status: CertStatus = "active"
    issued_at: date | None = None
    expires_at: date | None = None
    is_placeholder: bool = False
    document_url: str | None = None
    notes: str | None = None


class CertificateCreate(CertificateBase):
    supplier_ids: list[int] = []


class CertificateUpdate(BaseModel):
    cert_number: str | None = None
    scheme: str | None = None
    status: CertStatus | None = None
    issued_at: date | None = None
    expires_at: date | None = None
    is_placeholder: bool | None = None
    document_url: str | None = None
    notes: str | None = None
    supplier_ids: list[int] | None = None


class CertificateRead(CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_ids: list[int] = []
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    # Parser-derived read-only fields (migration 0034 — F0-F/F0-H finding).
    # Populated by `scripts/backfill_cert_scope.py` reading the supplier PDF;
    # not user-settable. Surfaced so the auditor UI can compare DB-`scheme`
    # against `scheme_pdf_detected` (round-2 finding N4 scheme-mismatch badge)
    # and inspect the original scope text without re-extracting the PDF.
    pdf_ref: str | None = None
    scope_material_groups: list[str] | None = None
    scope_raw: str | None = None
    scope_parsed_at: datetime | None = None
    scheme_pdf_detected: str | None = None
