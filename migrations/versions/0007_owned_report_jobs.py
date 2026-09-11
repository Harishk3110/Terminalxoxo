"""Private immutable-input report queue."""

import sqlalchemy as sa
from alembic import op

revision = "0007_owned_report_jobs"
down_revision = "0006_auth_totp_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("worker_id", sa.String(120)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_category", sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("object_key", sa.String(500)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_jobs_user_id", "report_jobs", ["user_id"])
    op.create_index("ix_report_jobs_status", "report_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("report_jobs")
