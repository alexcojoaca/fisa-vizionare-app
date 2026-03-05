"""Add session_version to user for admin 'logout other devices'.

Revision ID: f031_session_version
Revises: f030_agent_phone
Create Date: 2025-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "f031_session_version"
down_revision = "f030_agent_phone"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("session_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )


def downgrade():
    op.drop_column("user", "session_version")
