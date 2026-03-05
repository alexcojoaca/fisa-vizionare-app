"""Add announcement, user_announcement_read tables and user.expiry_reminder_dismissed_at.

Revision ID: f016_announcements_expiry_reminder
Revises: f015_drop_assistant_reminder
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "f016_announcements_expiry_reminder"
down_revision = "f015_drop_assistant_reminder"
branch_labels = None
depends_on = None


def upgrade():
    # user.expiry_reminder_dismissed_at
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expiry_reminder_dismissed_at", sa.DateTime(timezone=True), nullable=True))

    # announcement
    op.create_table(
        "announcement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("announcement", schema=None) as batch_op:
        batch_op.create_index("ix_announcement_created_at", ["created_at"], unique=False)

    # user_announcement_read
    op.create_table(
        "user_announcement_read",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["announcement_id"], ["announcement.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "announcement_id"),
    )


def downgrade():
    op.drop_table("user_announcement_read")
    with op.batch_alter_table("announcement", schema=None) as batch_op:
        batch_op.drop_index("ix_announcement_created_at")
    op.drop_table("announcement")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("expiry_reminder_dismissed_at")
