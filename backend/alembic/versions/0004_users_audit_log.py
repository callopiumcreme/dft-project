"""users and audit_log tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-07

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column(
            "role",
            sa.String(20),
            sa.CheckConstraint(
                "role IN ('admin', 'operator', 'viewer', 'certifier')",
                name="ck_users_role",
            ),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_login_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_role", "users", ["role"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("table_name", sa.String(50), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_audit_log_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index("idx_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("idx_audit_log_table_record", "audit_log", ["table_name", "record_id"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_log_created_at", table_name="audit_log")
    op.drop_index("idx_audit_log_table_record", table_name="audit_log")
    op.drop_index("idx_audit_log_user_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
