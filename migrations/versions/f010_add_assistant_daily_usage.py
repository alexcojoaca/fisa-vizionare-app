"""Add assistant_daily_usage table for Gemini rate limit.

Revision ID: f010_assistant_daily_usage
Revises: f009_assistant_watchlist
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "f010_assistant_daily_usage"
down_revision = "f009_assistant_watchlist"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistant_daily_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_assistant_daily_user_date"),
    )
    with op.batch_alter_table("assistant_daily_usage", schema=None) as batch_op:
        batch_op.create_index("ix_assistant_daily_user_date", ["user_id", "usage_date"], unique=False)


def downgrade():
    with op.batch_alter_table("assistant_daily_usage", schema=None) as batch_op:
        batch_op.drop_index("ix_assistant_daily_user_date")
    op.drop_table("assistant_daily_usage")
