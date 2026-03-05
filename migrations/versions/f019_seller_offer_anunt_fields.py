"""Seller offer as anunt: price, surfaces, etaj, year, parking, commission; remove urgent.

Revision ID: f019_seller_offer_anunt
Revises: f018_seller_offer_like_cereri
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f019_seller_offer_anunt"
down_revision = "f018_seller_offer_like_cereri"
branch_labels = None
depends_on = None


def upgrade():
    # Drop index that includes urgent before dropping the column (SQLite)
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_index("ix_seller_offer_type_prop_urgent", if_exists=True)
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("surface_utila", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("surface_totala", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("surface_balcon", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("surface_terasa", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("surface_curte", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("etaj", sa.String(80), nullable=True))  # e.g. "P,1,2"
        batch_op.add_column(sa.Column("anul_constructiei", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("nr_locuri_parcare", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("offers_commission", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("commission_value", sa.String(80), nullable=True))
        batch_op.drop_column("urgent")
        batch_op.create_index("ix_seller_offer_type_prop", ["request_type", "property_type"], unique=False)
    # Backfill price from budget_min for existing rows
    op.execute(
        "UPDATE seller_offer SET price = budget_min WHERE price IS NULL AND budget_min IS NOT NULL"
    )


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_index("ix_seller_offer_type_prop", if_exists=True)
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("urgent", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_seller_offer_type_prop_urgent", ["request_type", "property_type", "urgent"], unique=False)
        batch_op.drop_column("commission_value")
        batch_op.drop_column("offers_commission")
        batch_op.drop_column("nr_locuri_parcare")
        batch_op.drop_column("anul_constructiei")
        batch_op.drop_column("etaj")
        batch_op.drop_column("surface_curte")
        batch_op.drop_column("surface_terasa")
        batch_op.drop_column("surface_balcon")
        batch_op.drop_column("surface_totala")
        batch_op.drop_column("surface_utila")
        batch_op.drop_column("price")
