"""Add cleanup_run table and user.last_login_at.

Revision ID: f014_cleanup_run_last_login
Revises: f013_marketplace_alert_request_property_type
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "f014_cleanup_run_last_login"
down_revision = "f013_marketplace_alert_request_property_type"
branch_labels = None
depends_on = None


def upgrade():
    # user.last_login_at
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # cleanup_run
    op.create_table(
        "cleanup_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ran_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ran_by_user_id", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ran_by_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("cleanup_run", schema=None) as batch_op:
        batch_op.create_index("ix_cleanup_run_ran_at", ["ran_at"], unique=False)
        batch_op.create_index("ix_cleanup_run_ran_by_user", ["ran_by_user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("cleanup_run", schema=None) as batch_op:
        batch_op.drop_index("ix_cleanup_run_ran_at")
        batch_op.drop_index("ix_cleanup_run_ran_by_user")
    op.drop_table("cleanup_run")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("last_login_at")
