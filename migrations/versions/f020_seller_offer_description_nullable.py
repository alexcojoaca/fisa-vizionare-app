"""Make seller_offer.description nullable.

Revision ID: f020_seller_offer_desc_nullable
Revises: f019_seller_offer_anunt
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f020_seller_offer_desc_nullable"
down_revision = "f019_seller_offer_anunt"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.alter_column(
            "description",
            existing_type=sa.Text(),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.alter_column(
            "description",
            existing_type=sa.Text(),
            nullable=False,
        )
