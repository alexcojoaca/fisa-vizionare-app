"""Add assistant_watchlist table.

Revision ID: f009_assistant_watchlist
Revises: f008_normalize_role
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "f009_assistant_watchlist"
down_revision = "f008_normalize_role"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistant_watchlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("zone", sa.String(120), nullable=True),
        sa.Column("price_min", sa.Integer(), nullable=True),
        sa.Column("price_max", sa.Integer(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("assistant_watchlist", schema=None) as batch_op:
        batch_op.create_index("ix_assistant_watchlist_user", ["user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("assistant_watchlist", schema=None) as batch_op:
        batch_op.drop_index("ix_assistant_watchlist_user")
    op.drop_table("assistant_watchlist")
