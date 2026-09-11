"""Persist expiring TOTP enrollment challenges and anti-replay counters."""

import sqlalchemy as sa
from alembic import op

revision = "0006_auth_totp_state"
down_revision = "0005_accounting_subledgers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_totp_states",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("last_timecode", sa.BigInteger(), nullable=False),
        sa.Column("pending_secret", sa.Text()),
        sa.Column("pending_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auth_totp_states")
