"""Persist terminal layouts, analytic jobs and labelled demo fundamentals."""
from alembic import op
from app.models import AnalysisRun, FundamentalSnapshot, WorkspaceState

revision = "0002_terminal_workspace"
down_revision = "0001_core_schema"
branch_labels = None
depends_on = None


def upgrade():
    for model in (WorkspaceState, AnalysisRun, FundamentalSnapshot):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in (FundamentalSnapshot, AnalysisRun, WorkspaceState):
        model.__table__.drop(op.get_bind(), checkfirst=True)
