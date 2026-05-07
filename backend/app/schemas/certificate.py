from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

CertificateStatus = Literal["active", "expired", "suspended"]
CertificateScheme = Literal["ISCC", "RSPO", "RTRS", "REDcert", "SQC"]


class CertificateBase(BaseModel):
    cert_number: str
    supplier_id: int
    issued_at: date
    expires_at: date | None = None
    scheme: str = "ISCC"
    status: CertificateStatus = "active"
    document_url: str | None = None


class CertificateCreate(CertificateBase):
    pass


class CertificateUpdate(BaseModel):
    cert_number: str | None = None
    supplier_id: int | None = None
    issued_at: date | None = None
    expires_at: date | None = None
    scheme: str | None = None
    status: CertificateStatus | None = None
    document_url: str | None = None


class CertificateRead(CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
