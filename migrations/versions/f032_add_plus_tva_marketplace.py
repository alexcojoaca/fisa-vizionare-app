"""Add plus_tva to buyer_request and seller_offer.

Revision ID: f032_plus_tva
Revises: f031_session_version
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "f032_plus_tva"
down_revision = "f031_session_version"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plus_tva", sa.Boolean(), nullable=False, server_default="0"))
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plus_tva", sa.Boolean(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_column("plus_tva")
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.drop_column("plus_tva")
