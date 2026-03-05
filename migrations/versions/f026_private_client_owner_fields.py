"""Câmpuri private: client_phone_private (cereri), owner_name_private (oferte). Vizibile doar proprietarului.

Revision ID: f026_private
Revises: f025_zones_full
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f026_private"
down_revision = "f025_zones_full"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("client_phone_private", sa.String(length=32), nullable=True))
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_name_private", sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_column("owner_name_private")
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.drop_column("client_phone_private")
