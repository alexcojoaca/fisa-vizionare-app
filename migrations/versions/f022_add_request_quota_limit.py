"""Add request_quota_limit to user for cereri.

Revision ID: f022_request_quota
Revises: f021_seller_offer_nr_etaje
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f022_request_quota"
down_revision = "f021_seller_offer_nr_etaje"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("request_quota_limit", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("request_quota_limit")
