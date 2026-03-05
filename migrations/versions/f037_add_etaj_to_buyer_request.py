"""Add etaj field to buyer_request for client floor preferences.

Revision ID: f037_etaj
Revises: f036_client
Create Date: 2026-02-11

- buyer_request.etaj: comma-separated floor preferences (Demisol, Parter, 1-18)
"""
from alembic import op
import sqlalchemy as sa


revision = "f037_etaj"
down_revision = "f036_client"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("etaj", sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.drop_column("etaj")
