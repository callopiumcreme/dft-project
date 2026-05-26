"""certificates: AUDIT-MISMATCH annotation for LITOPLAS / ECOGRAS bindings

Context: post-red-team round 1 evidence review (DEL-CRW-2025-2 audit, 2026-05-26)
flagged a mismatch between the cert PDF header and the supplier_certificates
binding on two ISCC EU certs:

  CO222-00000026 — PDF header: LITOPLAS SA
    Bound to: ESENTTIA, LE5TON, LITOPLAS (3 suppliers)
  ES216-20254036 — PDF header: CI ECOGRAS COLOMBIA SAS
    Bound to: LE5TON, LITOPLAS (2 suppliers; no `ECOGRAS` supplier exists)

Q3 2025 mass-balance impact verified zero: no `daily_inputs` rows reference
either cert with these suppliers in 2025-07-01 → 2025-09-30 window. So the
binding sits as a latent metadata error, not a current compliance liability.

The cliente data-request letter (docs/audit-dft-c1-cliente-data-request.md
section 7) asks Paolo Ughetti to clarify the commercial relationship before
any binding is modified. This migration is the audit-trail companion: it
records the mismatch inline in `certificates.notes` so an auditor inspecting
the table sees the flag without having to cross-reference the docs/ folder.

What this migration DOES:
- Appends an `AUDIT-MISMATCH 2026-05-26:` line to `certificates.notes` for
  the two affected certs (matched by `cert_number`, not by id, per the
  migration-row-id-portability lesson).
- Preserves the pre-existing `shared multi-supplier` note.

What this migration DOES NOT do:
- No change to `supplier_certificates` bindings.
- No soft-delete on certificates.
- No change to `daily_inputs.certificate_id` references.
- No status change on the certificates (they remain `active`).

A follow-up migration 0037 will perform the actual soft-deprecate of any
binding the cliente confirms as erroneous. That migration is not pre-written
to avoid biasing the decision toward one resolution.

Downgrade: removes the appended line, restoring notes to its prior value.
The match is by exact substring so re-running upgrade/downgrade is
idempotent.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0035_cert_audit_mismatch"
down_revision = "0034_cert_scope_material_groups"
branch_labels = None
depends_on = None

ANNOTATION_LITOPLAS = (
    "AUDIT-MISMATCH 2026-05-26: PDF intestazione = LITOPLAS SA; binding "
    "include ESENTTIA + LE5TON oltre LITOPLAS. Pending verifica relazione "
    "commerciale per Paolo Ughetti (cf. docs/audit-dft-c1-cliente-data-"
    "request.md §7). Soft-deprecate sospeso fino chiarimento cliente."
)

ANNOTATION_ECOGRAS = (
    "AUDIT-MISMATCH 2026-05-26: PDF intestazione = CI ECOGRAS COLOMBIA SAS; "
    "binding include LE5TON + LITOPLAS (nessun supplier ECOGRAS esiste in "
    "anagrafica). Pending verifica chain custody trader per Paolo Ughetti "
    "(cf. docs/audit-dft-c1-cliente-data-request.md §7). Soft-deprecate "
    "sospeso fino chiarimento cliente."
)

# Use a sentinel separator so downgrade can find and strip the annotation
# without disturbing any prior or subsequent text.
SEP = " | "


def upgrade() -> None:
    """Append the audit-mismatch annotation to the two certs."""
    bind = op.get_bind()

    for cert_number, annotation in (
        ("CO222-00000026", ANNOTATION_LITOPLAS),
        ("ES216-20254036", ANNOTATION_ECOGRAS),
    ):
        bind.execute(
            sa.text(
                """
                UPDATE certificates
                SET notes = CASE
                    WHEN notes IS NULL OR notes = '' THEN :annotation
                    WHEN position(:annotation IN notes) > 0 THEN notes
                    ELSE notes || :sep || :annotation
                END,
                updated_at = now()
                WHERE cert_number = :cert_number
                """
            ),
            {"cert_number": cert_number, "annotation": annotation, "sep": SEP},
        )


def downgrade() -> None:
    """Strip the audit-mismatch annotation from the two certs."""
    bind = op.get_bind()

    for cert_number, annotation in (
        ("CO222-00000026", ANNOTATION_LITOPLAS),
        ("ES216-20254036", ANNOTATION_ECOGRAS),
    ):
        # Try the form with separator first (notes had prior content).
        bind.execute(
            sa.text(
                """
                UPDATE certificates
                SET notes = replace(notes, :with_sep, ''),
                    updated_at = now()
                WHERE cert_number = :cert_number
                  AND position(:with_sep IN notes) > 0
                """
            ),
            {
                "cert_number": cert_number,
                "with_sep": SEP + annotation,
            },
        )
        # And the bare form (notes was empty at upgrade time).
        bind.execute(
            sa.text(
                """
                UPDATE certificates
                SET notes = NULL,
                    updated_at = now()
                WHERE cert_number = :cert_number
                  AND notes = :annotation
                """
            ),
            {"cert_number": cert_number, "annotation": annotation},
        )
