"""PAdES-B PDF signing service — closes DFTEN-177 (E8-G7).

Wraps pyhanko's ``SimpleSigner`` / ``PdfSigner`` to apply a PAdES-B
(``ETSI.CAdES.detached`` subfilter) digital signature to an existing PDF.
Used by:

    * RTFO verifier bundle pipeline (final-step signing of the concatenated
      ``verifier-bundle-c{id}-{date}.pdf``).
    * One-off ``POST /sign/pdf`` admin endpoint for ad-hoc signing of
      bundle artefacts under approved roots.

Determinism note:
    Digital signatures embed a signing timestamp and a CMS object, so the
    signed PDF is **NOT** byte-stable across runs (each ``sign`` produces a
    fresh signature). The pre-sign SHA-256 of the unsigned input is
    deterministic (matches the renderer's hash); the post-sign SHA-256
    therefore differs and the test suite asserts that it differs.

Public API:
    sign_pdf(input_path, output_path, pkcs12_path, passphrase, signer_name)
        -> SignResult
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata, PdfSigner

# Repo-root anchored signing material location (gitignored via data/).
# backend/app/services/pdf_signer.py → parents[3] == repo root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DEFAULT_PKCS12_PATH: Final[Path] = _REPO_ROOT / "data" / "signing" / "dev_cert.p12"
DEFAULT_PASSPHRASE: Final[str] = "dft-dev-signer"  # noqa: S105 — dev-only PKCS#12 secret
DEFAULT_SIGNER_NAME: Final[str] = "DFT verifier"

# PAdES-B baseline = CAdES-detached subfilter + DocMDP perm 2 (form fill + sign).
_SUBFILTER: Final[SigSeedSubFilter] = SigSeedSubFilter.PADES


class PDFSignError(RuntimeError):
    """Raised when signing fails (bad cert, bad path, bad PDF)."""


@dataclass(frozen=True, slots=True)
class SignResult:
    """Outcome of a successful sign — all fields populated, paths absolute."""

    input_path: Path
    output_path: Path
    sha256_before: str
    sha256_after: str
    signer_subject: str
    algorithm: str
    signed_at: datetime
    output_size_bytes: int


def _sha256_file(path: Path) -> str:
    """Stream a file through SHA-256 (avoids loading the whole PDF in RAM)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_subject(signer: signers.SimpleSigner) -> str:
    """Pretty CN/O subject string from the loaded signer's X.509 cert."""
    cert = signer.signing_cert
    if cert is None:  # pragma: no cover — load_pkcs12 always populates this
        return "(unknown)"
    # asn1crypto.x509.Certificate exposes subject.human_friendly
    subj = cert.subject
    try:
        return str(subj.human_friendly)
    except (AttributeError, TypeError):  # pragma: no cover
        return str(subj)


def _prepare_signer(
    input_path: Path,
    output_path: Path,
    pkcs12_path: Path | None,
    passphrase: str | None,
    signer_name: str,
) -> tuple[signers.SimpleSigner, PdfSigner, str, str]:
    """Shared setup for sync + async sign paths: load cert, build PdfSigner,
    compute pre-sign SHA-256 + signer subject DN."""
    if not input_path.is_file():
        raise PDFSignError(f"input PDF not found: {input_path}")

    pkcs12 = pkcs12_path or DEFAULT_PKCS12_PATH
    if not pkcs12.is_file():
        raise PDFSignError(
            f"PKCS#12 bundle not found: {pkcs12} — run scripts/gen_signing_cert.sh"
        )
    pw = (passphrase if passphrase is not None else DEFAULT_PASSPHRASE).encode("utf-8")

    sha_before = _sha256_file(input_path)

    try:
        simple_signer = signers.SimpleSigner.load_pkcs12(  # type: ignore[no-untyped-call]
            pfx_file=str(pkcs12),
            passphrase=pw,
        )
    except Exception as exc:
        raise PDFSignError(f"failed to load PKCS#12 bundle: {exc}") from exc

    if simple_signer is None:
        raise PDFSignError("SimpleSigner.load_pkcs12 returned None")

    subject = _extract_subject(simple_signer)

    signature_meta = PdfSignatureMetadata(
        field_name="DFTVerifierSig",
        subfilter=_SUBFILTER,
        name=signer_name,
        reason="DFT verifier bundle attestation",
        location="Baar, Switzerland",
    )
    pdf_signer = PdfSigner(
        signature_meta=signature_meta,
        signer=simple_signer,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return simple_signer, pdf_signer, sha_before, subject


def sign_pdf(
    input_path: Path,
    output_path: Path,
    *,
    pkcs12_path: Path | None = None,
    passphrase: str | None = None,
    signer_name: str = DEFAULT_SIGNER_NAME,
) -> SignResult:
    """Apply a PAdES-B signature to *input_path* and write to *output_path*.

    Args:
        input_path:  Absolute path to the unsigned source PDF.
        output_path: Absolute path for the signed output. Parent dir is
            auto-created. Overwrites if present (signing is not idempotent —
            each call produces a fresh signature).
        pkcs12_path: Path to a PKCS#12 bundle holding cert + private key.
            Defaults to the repo-local ``data/signing/dev_cert.p12`` produced
            by ``scripts/gen_signing_cert.sh``.
        passphrase:  PKCS#12 archive passphrase. Defaults to the dev value.
        signer_name: Human-readable signer name embedded in the signature
            field (``Name`` / ``/Name`` entry).

    Returns:
        SignResult with pre/post SHA-256, subject DN, algorithm tag, signed-at
        timestamp (UTC), and output size in bytes.

    Raises:
        PDFSignError: input not found, PKCS#12 not found, or pyhanko raises.
    """
    _simple_signer, pdf_signer, sha_before, subject = _prepare_signer(
        input_path, output_path, pkcs12_path, passphrase, signer_name
    )
    signed_at = datetime.now(UTC)

    try:
        with input_path.open("rb") as src, output_path.open("wb") as dst:
            writer = IncrementalPdfFileWriter(src)
            pdf_signer.sign_pdf(writer, output=dst)
    except Exception as exc:
        raise PDFSignError(f"sign_pdf failed: {exc}") from exc

    sha_after = _sha256_file(output_path)
    size = output_path.stat().st_size

    return SignResult(
        input_path=input_path,
        output_path=output_path,
        sha256_before=sha_before,
        sha256_after=sha_after,
        signer_subject=subject,
        algorithm="PAdES-B",
        signed_at=signed_at,
        output_size_bytes=size,
    )


async def async_sign_pdf(
    input_path: Path,
    output_path: Path,
    *,
    pkcs12_path: Path | None = None,
    passphrase: str | None = None,
    signer_name: str = DEFAULT_SIGNER_NAME,
) -> SignResult:
    """Async PAdES-B sign — calls ``PdfSigner.async_sign_pdf`` so it can be
    invoked from inside a running asyncio event loop (FastAPI routes).

    Semantics are identical to ``sign_pdf``; see that function's docstring.
    """
    _simple_signer, pdf_signer, sha_before, subject = _prepare_signer(
        input_path, output_path, pkcs12_path, passphrase, signer_name
    )
    signed_at = datetime.now(UTC)

    try:
        with input_path.open("rb") as src, output_path.open("wb") as dst:
            writer = IncrementalPdfFileWriter(src)
            await pdf_signer.async_sign_pdf(writer, output=dst)
    except Exception as exc:
        raise PDFSignError(f"async_sign_pdf failed: {exc}") from exc

    sha_after = _sha256_file(output_path)
    size = output_path.stat().st_size

    return SignResult(
        input_path=input_path,
        output_path=output_path,
        sha256_before=sha_before,
        sha256_after=sha_after,
        signer_subject=subject,
        algorithm="PAdES-B",
        signed_at=signed_at,
        output_size_bytes=size,
    )
