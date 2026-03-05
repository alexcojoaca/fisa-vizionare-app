"""Add offer_paid_slots, offer_paid_slots_expires_at, request_paid_slots, request_paid_slots_expires_at to user.

Revision ID: f023_paid_slots
Revises: f022_request_quota
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f023_paid_slots"
down_revision = "f022_request_quota"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("offer_paid_slots", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("offer_paid_slots_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("request_paid_slots", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("request_paid_slots_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("request_paid_slots_expires_at")
        batch_op.drop_column("request_paid_slots")
        batch_op.drop_column("offer_paid_slots_expires_at")
        batch_op.drop_column("offer_paid_slots")
