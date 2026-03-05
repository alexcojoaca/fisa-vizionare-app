"""Add to seller_offer: request_type, property_type, budget, rooms, year, urgent, contact_phone (same as cereri).

Revision ID: f018_seller_offer_like_cereri
Revises: f017_seller_offer_quota
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "f018_seller_offer_like_cereri"
down_revision = "f017_seller_offer_quota"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("request_type", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("property_type", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("budget_min", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("budget_max", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rooms", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("year_min", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("year_max", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("urgent", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("contact_phone", sa.String(32), nullable=True))
    # Make title nullable for backwards compat (optional for new offers)
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.alter_column("title", existing_type=sa.String(200), nullable=True)


def downgrade():
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.drop_column("contact_phone")
        batch_op.drop_column("urgent")
        batch_op.drop_column("year_max")
        batch_op.drop_column("year_min")
        batch_op.drop_column("rooms")
        batch_op.drop_column("budget_max")
        batch_op.drop_column("budget_min")
        batch_op.drop_column("property_type")
        batch_op.drop_column("request_type")
        batch_op.alter_column("title", existing_type=sa.String(200), nullable=False)
