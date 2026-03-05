"""Add seller_offer, offer_zones and user.offer_quota_limit.

Revision ID: f017_seller_offer_quota
Revises: f016_announcements_expiry_reminder
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa
from datetime import timezone


revision = "f017_seller_offer_quota"
down_revision = "f016_announcements_expiry_reminder"
branch_labels = None
depends_on = None


def upgrade():
    # user.offer_quota_limit (null = default 3 for paid users)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("offer_quota_limit", sa.Integer(), nullable=True))

    # seller_offer
    op.create_table(
        "seller_offer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("seller_offer", schema=None) as batch_op:
        batch_op.create_index("ix_seller_offer_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_seller_offer_created_at", ["created_at"], unique=False)

    # offer_zones
    op.create_table(
        "offer_zones",
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["seller_offer.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["zone.id"]),
        sa.PrimaryKeyConstraint("offer_id", "zone_id"),
    )
    with op.batch_alter_table("offer_zones", schema=None) as batch_op:
        batch_op.create_index("ix_offer_zones_zone_offer", ["zone_id", "offer_id"], unique=False)


def downgrade():
    op.drop_table("offer_zones")
    op.drop_table("seller_offer")
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("offer_quota_limit")
