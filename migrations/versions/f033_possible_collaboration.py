"""Add possible_collaboration and collaboration_seen tables.

Revision ID: f033_collab
Revises: f032_plus_tva
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "f033_collab"
down_revision = "f032_plus_tva"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "possible_collaboration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["seller_offer.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["buyer_request.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id", "request_id", name="uq_possible_collaboration_offer_request"),
    )
    op.create_index("ix_possible_collaboration_offer_id", "possible_collaboration", ["offer_id"])
    op.create_index("ix_possible_collaboration_request_id", "possible_collaboration", ["request_id"])
    op.create_index("ix_possible_collaboration_created", "possible_collaboration", ["created_at"])

    op.create_table(
        "collaboration_seen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collaboration_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collaboration_id"], ["possible_collaboration.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collaboration_id", "user_id", name="uq_collaboration_seen_user"),
    )
    op.create_index("ix_collaboration_seen_collaboration_id", "collaboration_seen", ["collaboration_id"])
    op.create_index("ix_collaboration_seen_user", "collaboration_seen", ["user_id"])


def downgrade():
    op.drop_table("collaboration_seen")
    op.drop_table("possible_collaboration")
