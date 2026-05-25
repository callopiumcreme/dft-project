"""Tests for pdf_signer service + POST /sign/pdf endpoint (DFTEN-177).

Covers:

* sign_pdf happy path — small generated PDF gets a valid PAdES-B signature.
* SHA-256 changes between before/after signing.
* pyhanko.sign.validation confirms intact + valid signature.
* Bad input path raises PDFSignError.
* POST /sign/pdf writes an audit_log row with action='pdf_sign' and the
  required meta keys.
* POST /sign/pdf rejects path-traversal (path outside approved roots).

The dev PKCS#12 bundle is regenerated via ``scripts/gen_signing_cert.sh``
at the start of the test session if missing, so the test is hermetic on
a fresh checkout.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from asn1crypto import pem, x509
from httpx import ASGITransport, AsyncClient
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from pypdf import PdfWriter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002 — used at runtime

from app.services.pdf_signer import (
    DEFAULT_PKCS12_PATH,
    PDFSignError,
    SignResult,
    sign_pdf,
)

# Repo root: backend/tests/test_pdf_signer.py → parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEV_PEM = _REPO_ROOT / "data" / "signing" / "dev_cert.pem"


# ---------------------------------------------------------------------------
# Session-scoped: ensure dev PKCS#12 exists before any test runs.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _ensure_dev_cert() -> None:
    if DEFAULT_PKCS12_PATH.is_file() and _DEV_PEM.is_file():
        return
    script = _REPO_ROOT / "scripts" / "gen_signing_cert.sh"
    subprocess.run(  # noqa: S603 — dev-only test bootstrap
        ["bash", str(script)],  # noqa: S607
        check=True,
        capture_output=True,
    )


@pytest.fixture
def tiny_pdf(tmp_path: Path) -> Path:
    """A minimal 1-page PDF, written to tmp_path."""
    out = tmp_path / "tiny.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    out.write_bytes(buf.getvalue())
    return out


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_sign_pdf_happy_path(tiny_pdf: Path, tmp_path: Path) -> None:
    """Sign a tiny PDF and verify the signature is intact + valid."""
    out = tmp_path / "tiny.signed.pdf"
    result = sign_pdf(input_path=tiny_pdf, output_path=out)

    assert isinstance(result, SignResult)
    assert result.output_path == out
    assert out.is_file()
    assert result.output_size_bytes > 0
    assert result.algorithm == "PAdES-B"
    # SHA-256 hex digests are 64 chars lowercase.
    assert len(result.sha256_before) == 64
    assert len(result.sha256_after) == 64
    # Signing changes the file → digests must differ.
    assert result.sha256_before != result.sha256_after
    # Subject DN must surface the dev cert CN.
    assert "DFT verifier" in result.signer_subject


def test_signed_pdf_validates_via_pyhanko(tiny_pdf: Path, tmp_path: Path) -> None:
    """The signed PDF round-trips through pyhanko's validator as intact+valid."""
    out = tmp_path / "tiny.signed.pdf"
    sign_pdf(input_path=tiny_pdf, output_path=out)

    pem_bytes = _DEV_PEM.read_bytes()
    _type, _hdrs, der = pem.unarmor(pem_bytes)
    trust_root = x509.Certificate.load(der)
    vc = ValidationContext(trust_roots=[trust_root])

    with out.open("rb") as fh:
        reader = PdfFileReader(fh)
        sigs = list(reader.embedded_signatures)
        assert len(sigs) == 1
        status = validate_pdf_signature(sigs[0], vc)
        assert status.intact is True
        assert status.valid is True


def test_sign_pdf_missing_input_raises(tmp_path: Path) -> None:
    """sign_pdf must raise PDFSignError when the input PDF does not exist."""
    bogus = tmp_path / "does_not_exist.pdf"
    out = tmp_path / "out.pdf"
    with pytest.raises(PDFSignError, match="input PDF not found"):
        sign_pdf(input_path=bogus, output_path=out)


def test_sign_pdf_missing_pkcs12_raises(tiny_pdf: Path, tmp_path: Path) -> None:
    """sign_pdf must raise PDFSignError when the PKCS#12 bundle is missing."""
    out = tmp_path / "out.pdf"
    bogus_p12 = tmp_path / "missing.p12"
    with pytest.raises(PDFSignError, match="PKCS#12 bundle not found"):
        sign_pdf(input_path=tiny_pdf, output_path=out, pkcs12_path=bogus_p12)


# ---------------------------------------------------------------------------
# Endpoint test: POST /sign/pdf writes audit_log row + rejects traversal
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def approved_bundle_pdf(db_session: AsyncSession) -> Any:
    """Drop a tiny PDF under data/verifier_bundles/test-c-pdf-signer/ for the test.

    Yields the relative path (str). After the test, the artefact + audit row
    are cleaned up.
    """
    approved_root = _REPO_ROOT / "data" / "verifier_bundles" / "test-c-pdf-signer"
    approved_root.mkdir(parents=True, exist_ok=True)

    target = approved_root / "verifier-bundle-test.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    target.write_bytes(buf.getvalue())

    rel = str(target.relative_to(_REPO_ROOT))
    yield rel

    # Cleanup: remove generated artefacts + audit rows tagged to this dir.
    for f in approved_root.glob("*"):
        f.unlink()
    approved_root.rmdir()
    await db_session.execute(
        text(
            """
            DELETE FROM audit_log
             WHERE action = 'pdf_sign'
               AND (new_values->>'input_path') LIKE
                   'data/verifier_bundles/test-c-pdf-signer/%'
            """
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_post_sign_pdf_writes_audit_row(
    approved_bundle_pdf: str,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """POST /sign/pdf signs the file and writes an audit_log row with the
    required meta keys."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/sign/pdf",
            json={"bundle_path": approved_bundle_pdf},
            headers=admin_headers,
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["algorithm"] == "PAdES-B"
    assert len(body["sha256_before"]) == 64
    assert len(body["sha256_after"]) == 64
    assert body["sha256_before"] != body["sha256_after"]
    assert "DFT verifier" in body["signer_subject"]
    assert body["audit_log_id"] > 0
    assert body["signed_path"].endswith(".signed.pdf")
    assert Path(body["signed_path"]).is_file()

    # Audit-log row check: action + required meta keys all present.
    row = (
        await db_session.execute(
            text(
                "SELECT action, new_values, changed_by FROM audit_log "
                "WHERE id = :id"
            ),
            {"id": body["audit_log_id"]},
        )
    ).mappings().one()
    assert row["action"] == "pdf_sign"
    assert row["changed_by"] == 1  # admin override user
    meta = row["new_values"]
    for key in (
        "input_path",
        "output_path",
        "sha256_before",
        "sha256_after",
        "signer_subject",
        "algo",
    ):
        assert key in meta, f"missing key {key} in audit_log.new_values"
    assert meta["algo"] == "PAdES-B"
    assert meta["sha256_before"] == body["sha256_before"]
    assert meta["sha256_after"] == body["sha256_after"]


@pytest.mark.asyncio
async def test_post_sign_pdf_rejects_path_traversal(
    admin_headers: dict[str, str],
) -> None:
    """Paths outside the approved roots must be rejected with 400."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/sign/pdf",
            json={"bundle_path": "../etc/passwd"},
            headers=admin_headers,
        )
    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"].lower() or "resolve" in resp.json()[
        "detail"
    ].lower()


@pytest.mark.asyncio
async def test_post_sign_pdf_requires_admin(
    operator_headers: dict[str, str],
) -> None:
    """Operator role must be rejected with 403."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/sign/pdf",
            json={"bundle_path": "data/verifier_bundles/whatever.pdf"},
            headers=operator_headers,
        )
    assert resp.status_code == 403
