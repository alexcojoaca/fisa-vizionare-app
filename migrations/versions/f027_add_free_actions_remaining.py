"""Add free_actions_remaining to user for limited free access tracking.

Revision ID: f027_free_actions
Revises: f026_private
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f027_free_actions"
down_revision = "f026_private"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("free_actions_remaining", sa.Integer(), nullable=False, server_default="3"))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("free_actions_remaining")
