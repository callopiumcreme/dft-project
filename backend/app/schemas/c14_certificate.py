from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class C14CertificateBase(BaseModel):
    cert_number: str
    lab: str | None = None
    product: str | None = None
    period_month: date | None = None
    sampled_date: date | None = None
    tested_date: date | None = None
    report_date: date | None = None
    bio_carbon_pct: Decimal | None = None
    method: str | None = None
    sample_ref: str | None = None
    batch_ref: str | None = None
    sustainability_decl: str | None = None
    pdf_filename: str | None = None
    notes: str | None = None


class C14CertificateCreate(C14CertificateBase):
    pass


class C14CertificateUpdate(BaseModel):
    cert_number: str | None = None
    lab: str | None = None
    product: str | None = None
    period_month: date | None = None
    sampled_date: date | None = None
    tested_date: date | None = None
    report_date: date | None = None
    bio_carbon_pct: Decimal | None = None
    method: str | None = None
    sample_ref: str | None = None
    batch_ref: str | None = None
    sustainability_decl: str | None = None
    pdf_filename: str | None = None
    notes: str | None = None


class C14CertificateRead(C14CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
