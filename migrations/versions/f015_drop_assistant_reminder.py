"""Drop assistant_reminder table (memento feature removed).

Revision ID: f015_drop_assistant_reminder
Revises: f014_cleanup_run_last_login
Create Date: 2026-02-07

"""
from alembic import op


revision = "f015_drop_assistant_reminder"
down_revision = "03ecb262ee25"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("assistant_reminder")


def downgrade():
    import sqlalchemy as sa

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
