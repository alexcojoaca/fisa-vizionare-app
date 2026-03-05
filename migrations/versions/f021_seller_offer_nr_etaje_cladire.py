"""Add nr_etaje_cladire to seller_offer; widen etaj for 1-30.

Revision ID: f021_seller_offer_nr_etaje
Revises: f020_seller_offer_desc_nullable
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f021_seller_offer_nr_etaje"
down_revision = "f020_seller_offer_desc_nullable"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nr_etaje_cladire", sa.Integer(), nullable=True))
        batch_op.alter_column("etaj", existing_type=sa.String(80), type_=sa.String(120), existing_nullable=True)


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_column("nr_etaje_cladire")
        batch_op.alter_column("etaj", existing_type=sa.String(120), type_=sa.String(80), existing_nullable=True)
