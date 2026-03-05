"""Add DailyActivity.total_amount, TeamMember.status, agent confirm flow.

Revision ID: f035_team_enh
Revises: f034_team
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "f035_team_enh"
down_revision = "f034_team"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("daily_activity", sa.Column("total_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("team_member", sa.Column("status", sa.String(20), nullable=False, server_default="confirmed"))
    op.create_index("ix_team_member_status", "team_member", ["status"])


def downgrade():
    op.drop_index("ix_team_member_status", "team_member")
    op.drop_column("team_member", "status")
    op.drop_column("daily_activity", "total_amount")
