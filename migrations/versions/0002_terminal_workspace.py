"""Persist terminal layouts, analytic jobs and labelled demo fundamentals."""

from alembic import op
from app.models import AnalysisRun, Base, FundamentalSnapshot, WorkspaceState

revision = "0002_terminal_workspace"
down_revision = "0001_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for model in (WorkspaceState, AnalysisRun, FundamentalSnapshot):
        Base.metadata.tables[model.__tablename__].create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for model in (FundamentalSnapshot, AnalysisRun, WorkspaceState):
        Base.metadata.tables[model.__tablename__].drop(op.get_bind(), checkfirst=True)
