"""Add price_negotiable to seller_offer.

Revision ID: f024_price_negotiable
Revises: f023_paid_slots
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f024_price_negotiable"
down_revision = "f023_paid_slots"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price_negotiable", sa.Boolean(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_column("price_negotiable")
