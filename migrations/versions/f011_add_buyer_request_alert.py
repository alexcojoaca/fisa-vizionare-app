"""Add buyer_request_alert table for marketplace alarms.

Revision ID: f011_buyer_request_alert
Revises: f010_assistant_daily_usage
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "f011_buyer_request_alert"
down_revision = "f010_assistant_daily_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "buyer_request_alert",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("zone_ids", sa.Text(), nullable=True),
        sa.Column("min_budget", sa.Integer(), nullable=True),
        sa.Column("max_budget", sa.Integer(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("buyer_request_alert", schema=None) as batch_op:
        batch_op.create_index("ix_buyer_request_alert_user", ["user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("buyer_request_alert", schema=None) as batch_op:
        batch_op.drop_index("ix_buyer_request_alert_user")
    op.drop_table("buyer_request_alert")
