"""audit_log: allow action='pdf_sign' for PAdES-B sign events

Story: DFTEN-177 (E8-G7). The PDF signer service (``services/pdf_signer``)
writes an audit_log row with ``action='pdf_sign'`` when a verifier-bundle
artefact is digitally signed via pyhanko's PAdES-B pipeline.

The pre-existing CHECK constraint ``audit_log_action_check`` only allowed
``insert / update / delete / soft_delete / restore`` (per migration 0001).
This migration relaxes the constraint to additionally allow ``pdf_sign``.

Schema-only; no data backfill. Down-revision drops the column-value
``pdf_sign`` is forbidden again — any signed-PDF rows must be deleted
first by the operator if the downgrade is ever exercised (it shouldn't
be).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0035_audit_log_pdf_sign_action"
down_revision = "0034_backfill_transload_pdf_ref"
branch_labels = None
depends_on = None


_OLD_ACTIONS = "'insert','update','delete','soft_delete','restore'"
_NEW_ACTIONS = "'insert','update','delete','soft_delete','restore','pdf_sign'"


def upgrade() -> None:
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_action_check")
    op.execute(
        f"ALTER TABLE audit_log ADD CONSTRAINT audit_log_action_check "
        f"CHECK (action IN ({_NEW_ACTIONS}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_action_check")
    op.execute(
        f"ALTER TABLE audit_log ADD CONSTRAINT audit_log_action_check "
        f"CHECK (action IN ({_OLD_ACTIONS}))"
    )
