"""certificates: scope_material_groups + scope_raw + scope_parsed_at + scheme_pdf_detected

Context: red-team round 1 (DEL-CRW-2025-2 audit, 2026-05-26) failure
mode F0-F — the DFT app has no machine-readable record of what each
ISCC EU certificate is actually scoped for at the *material* level.
Auditor cannot answer "is ELT in scope on cert X?" from the DB; they
must open the PDF, find the "Scope of certification" / "Material(s)
and product groups" block, and read it by eye.

Round 2 self-audit (same date) found a much more serious mode while
building the parser — failure mode **F0-H = SCHEME MISCLASSIFICATION**.
5/7 in-scope cert PDFs (LITOPLAS, ESENTTIA, PYRCOM, KALTIRE, EFFICIEN)
are **ISCC PLUS** documents — the circular-plastics schema — even
though the DB records them as ``scheme='ISCC EU'``.  UK RTFO accepts
ISCC EU + ISCC CORSIA, **not** ISCC PLUS, so those rows are non-
conformant for the DEL-CRW-2025-2 submission as currently labelled.

Per the ``project_iscc_audit_safety`` rule we MUST NOT silently
overwrite the historical ``scheme`` column.  Instead this migration
adds a parallel column ``scheme_pdf_detected`` that the parser
populates from the PDF text.  A mismatch between ``scheme`` and
``scheme_pdf_detected`` is surfaced (UI + lettera §8 to Paolo) for
cliente decision, not rewritten.

The ELT eligibility framing for the RTFO submission rests on each
upstream cert listing the right material group.  Without a column
holding the parsed list, the eligibility claim is unverifiable
without manual PDF inspection — a real audit blocker.

This migration adds three columns to `certificates`:

    * `scope_material_groups text[]` — normalised array of material
      group names (e.g. {'End-of-life tyres (ELT)', 'Used cooking
      oil (UCO)'}).  NULL = not yet parsed.  Empty array = parsed,
      no groups found (rare; usually means scope is "operator-only"
      with no material handling).
    * `scope_raw text` — exact substring lifted from the cert PDF
      between the "Scope of certification" header and the next
      section break.  Audit trail: lets a reviewer see *exactly*
      what the parser was looking at without re-running it.
    * `scope_parsed_at timestamptz` — when the parser last ran.
      NULL = never parsed.  Set on both successful and empty parses
      so the parser doesn't re-attempt every poll.

Plus a GIN index on the array column so filters like
``WHERE 'End-of-life tyres (ELT)' = ANY(scope_material_groups)``
hit the index.

Audit-aligned design:
    * No backfill.  The parser is a separate service
      (``app/services/cert_scope_parser.py``); backfill is run
      out-of-band via ``scripts/backfill_cert_scope.py`` once all
      7 in-scope cert PDFs are on disk (Tier A §8.2 confirmed they
      are, post `pdf_ref` rollout).
    * Nullable columns — historical certs without parsed scope
      stay NULL and surface as "scope unknown" in the UI instead
      of pretending we know.
    * Re-runnable — the parser uses `scope_parsed_at` as a guard,
      not the column nullability, so a forced re-parse can update
      stale arrays after a parser fix.

Numbering note: this revision depends on
``0033_weighbridge_ticket_no``.  Both audit-handover branches
expect both columns to apply in sequence.  Sprint e8 branch has
its own 0033 + 0034 — collision resolved at merge time via rebase.

Downgrade drops index + 3 columns.  No data preservation: the
scope record's source of truth remains the cert PDF on disk.
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0034_cert_scope_material_groups"
down_revision = "0033_weighbridge_ticket_no"
branch_labels = None
depends_on = None


SCOPE_COL_COMMENT = (
    "Material groups parsed from cert PDF 'Scope of certification' "
    "block. NULL = not yet parsed; empty array = parsed, no groups "
    "(operator-only scope). Used for RTFO ELT eligibility verification "
    "(audit F0-F)."
)

RAW_COL_COMMENT = (
    "Verbatim substring from cert PDF — scope section as-is. Audit "
    "trail for what cert_scope_parser was looking at."
)

PARSED_AT_COL_COMMENT = (
    "When cert_scope_parser last ran. NULL = never parsed. Set on "
    "both successful + empty parses; re-parse is explicit, not "
    "nullability-driven."
)

SCHEME_DETECTED_COL_COMMENT = (
    "ISCC scheme parsed from cert PDF header — independent of the "
    "manually entered ``scheme`` column.  NULL = not yet parsed.  "
    "Mismatch between ``scheme`` and ``scheme_pdf_detected`` is a "
    "disclosure flag (audit F0-H, 2026-05-26 finding); the historical "
    "``scheme`` value is NEVER overwritten automatically."
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE certificates "
        "ADD COLUMN IF NOT EXISTS scope_material_groups text[], "
        "ADD COLUMN IF NOT EXISTS scope_raw text, "
        "ADD COLUMN IF NOT EXISTS scope_parsed_at timestamptz, "
        "ADD COLUMN IF NOT EXISTS scheme_pdf_detected text"
    )
    op.execute(
        f"COMMENT ON COLUMN certificates.scope_material_groups IS "
        f"$cmt${SCOPE_COL_COMMENT}$cmt$"
    )
    op.execute(
        f"COMMENT ON COLUMN certificates.scope_raw IS "
        f"$cmt${RAW_COL_COMMENT}$cmt$"
    )
    op.execute(
        f"COMMENT ON COLUMN certificates.scope_parsed_at IS "
        f"$cmt${PARSED_AT_COL_COMMENT}$cmt$"
    )
    op.execute(
        f"COMMENT ON COLUMN certificates.scheme_pdf_detected IS "
        f"$cmt${SCHEME_DETECTED_COL_COMMENT}$cmt$"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_certificates_scope_material_groups "
        "ON certificates USING gin (scope_material_groups)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_certificates_scheme_mismatch "
        "ON certificates (cert_number) "
        "WHERE scheme_pdf_detected IS NOT NULL "
        "AND scheme_pdf_detected <> scheme "
        "AND deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_certificates_scheme_mismatch")
    op.execute("DROP INDEX IF EXISTS ix_certificates_scope_material_groups")
    op.execute(
        "ALTER TABLE certificates "
        "DROP COLUMN IF EXISTS scheme_pdf_detected, "
        "DROP COLUMN IF EXISTS scope_parsed_at, "
        "DROP COLUMN IF EXISTS scope_raw, "
        "DROP COLUMN IF EXISTS scope_material_groups"
    )
