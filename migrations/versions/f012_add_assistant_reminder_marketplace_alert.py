"""Add assistant_reminder and marketplace_alert tables.

Revision ID: f012_assistant_reminder_marketplace_alert
Revises: f011_buyer_request_alert
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "f012_assistant_reminder_marketplace_alert"
down_revision = "f011_buyer_request_alert"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistant_reminder",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text_raw", sa.Text(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("assistant_reminder", schema=None) as batch_op:
        batch_op.create_index("ix_assistant_reminder_user", ["user_id"], unique=False)

    op.create_table(
        "marketplace_alert",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("zone_ids", sa.Text(), nullable=True),
        sa.Column("rooms_min", sa.Integer(), nullable=True),
        sa.Column("rooms_max", sa.Integer(), nullable=True),
        sa.Column("budget_min", sa.Integer(), nullable=True),
        sa.Column("budget_max", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_request_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("marketplace_alert", schema=None) as batch_op:
        batch_op.create_index("ix_marketplace_alert_user", ["user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("marketplace_alert", schema=None) as batch_op:
        batch_op.drop_index("ix_marketplace_alert_user")
    op.drop_table("marketplace_alert")
    with op.batch_alter_table("assistant_reminder", schema=None) as batch_op:
        batch_op.drop_index("ix_assistant_reminder_user")
    op.drop_table("assistant_reminder")
