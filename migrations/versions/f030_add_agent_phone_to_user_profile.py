"""Add agent_phone field to user_profile.

Revision ID: f030_agent_phone
Revises: f029_free_viewing_flags
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "f030_agent_phone"
down_revision = "f029_free_viewing_flags"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_profile", schema=None) as batch_op:
        batch_op.add_column(sa.Column("agent_phone", sa.String(length=20), nullable=False, server_default=""))


def downgrade():
    with op.batch_alter_table("user_profile", schema=None) as batch_op:
        batch_op.drop_column("agent_phone")
