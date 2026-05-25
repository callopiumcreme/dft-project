"""PDF signing router — admin-only PAdES-B sign endpoint.

Story: DFTEN-177 (E8-G7). Wraps ``services/pdf_signer.sign_pdf`` behind
``POST /sign/pdf``. The endpoint:

    1. Validates that ``bundle_path`` resolves under an approved root
       (path-traversal guard via ``Path.resolve().relative_to(root)``).
    2. Signs in-place under the same approved root with a ``.signed.pdf``
       suffix (e.g. ``foo.pdf`` → ``foo.signed.pdf``).
    3. Writes an ``audit_log`` row with ``action='pdf_sign'`` and meta:
       ``{input_path, output_path, sha256_before, sha256_after,
          signer_subject, algo: 'PAdES-B'}``.
    4. Returns the artefact paths + both hashes + subject DN.

Approved roots (each is the relative bind-mount path under repo root):

    * ``data/verifier_bundles/``  — RTFO multi-section bundles
    * ``data/transload/``         — UTB transload consolidated PDFs
    * ``data/delivery_uk/``       — Crown Oil UK delivery PDFs

Roots are anchored at repo-root (``parents[3]`` from this file). Any path
that does not resolve under one of them returns 400.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — used at runtime by Pydantic model field
from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser  # noqa: TC001 — Annotated dep used at runtime
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.services.pdf_signer import PDFSignError, async_sign_pdf

router = APIRouter(prefix="/sign", tags=["sign"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

# Repo-root anchored approved roots. backend/app/routers/signing.py
# → parents[3] == repo root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
APPROVED_ROOTS: Final[tuple[Path, ...]] = (
    _REPO_ROOT / "data" / "verifier_bundles",
    _REPO_ROOT / "data" / "transload",
    _REPO_ROOT / "data" / "delivery_uk",
)


class SignRequest(BaseModel):
    """POST /sign/pdf body — single ``bundle_path`` relative or absolute."""

    model_config = ConfigDict(extra="forbid")

    bundle_path: str = Field(
        ...,
        description=(
            "Path to the unsigned PDF, relative to repo root or absolute. "
            "Must resolve under one of data/verifier_bundles/, data/transload/, "
            "or data/delivery_uk/."
        ),
        min_length=1,
    )
    signer_name: str = Field(
        default="DFT verifier",
        description="Human-readable signer name embedded in the /Name entry.",
        min_length=1,
        max_length=128,
    )


class SignResponse(BaseModel):
    """POST /sign/pdf response — paths + hashes + subject."""

    model_config = ConfigDict(extra="forbid")

    signed_path: str
    sha256_before: str
    sha256_after: str
    signer_subject: str
    algorithm: str
    signed_at: datetime
    output_size_bytes: int
    audit_log_id: int


def _resolve_under_approved(raw: str) -> Path:
    """Resolve *raw* and assert it lives under one of APPROVED_ROOTS.

    Accepts both absolute paths and paths relative to ``_REPO_ROOT``.

    Raises:
        HTTPException 400 — path escapes the approved roots.
        HTTPException 404 — path resolves cleanly but the file is missing.
    """
    p = Path(raw)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    try:
        resolved = p.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid path: {exc}",
        ) from exc
    for root in APPROVED_ROOTS:
        try:
            resolved.relative_to(root.resolve(strict=False))
            break
        except ValueError:
            continue
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "bundle_path must resolve under data/verifier_bundles/, "
                "data/transload/, or data/delivery_uk/"
            ),
        )
    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF not found: {resolved}",
        )
    return resolved


@router.post("/pdf", response_model=SignResponse)
async def sign_pdf_endpoint(
    body: SignRequest,
    user: AdminUser,
    db: DbDep,
) -> SignResponse:
    """Sign a PDF artefact and write an audit_log row. Admin-only.

    The signed output sits next to the input with a ``.signed.pdf`` suffix
    so the original is preserved (audit trail invariant). Re-signing the
    same input overwrites the previous signed file (signing is non-
    idempotent — each call carries a fresh timestamp / signature).
    """
    input_path = _resolve_under_approved(body.bundle_path)

    # Output: <stem>.signed.pdf next to the input. If the input is already
    # *.signed.pdf, allow re-signing by appending another .signed (rare).
    stem = input_path.stem
    if input_path.name.endswith(".signed.pdf"):
        # already-signed input — overwrite the signature with a fresh one.
        output_path = input_path
    else:
        output_path = input_path.with_name(f"{stem}.signed.pdf")

    try:
        result = await async_sign_pdf(
            input_path=input_path,
            output_path=output_path,
            signer_name=body.signer_name,
        )
    except PDFSignError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"sign failed: {exc}",
        ) from exc

    audit = AuditLog(
        table_name="pdf_artefact",
        record_id=0,  # no FK target — this is a signing event, not a row mutation
        action="pdf_sign",
        old_values=None,
        new_values={
            "input_path": str(result.input_path.relative_to(_REPO_ROOT))
            if result.input_path.is_relative_to(_REPO_ROOT)
            else str(result.input_path),
            "output_path": str(result.output_path.relative_to(_REPO_ROOT))
            if result.output_path.is_relative_to(_REPO_ROOT)
            else str(result.output_path),
            "sha256_before": result.sha256_before,
            "sha256_after": result.sha256_after,
            "signer_subject": result.signer_subject,
            "algo": result.algorithm,
        },
        changed_by=user.id,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return SignResponse(
        signed_path=str(result.output_path),
        sha256_before=result.sha256_before,
        sha256_after=result.sha256_after,
        signer_subject=result.signer_subject,
        algorithm=result.algorithm,
        signed_at=result.signed_at,
        output_size_bytes=result.output_size_bytes,
        audit_log_id=audit.id,
    )
