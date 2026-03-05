"""Add client role support: phone field in user, client commission fields in buyer_request.

Revision ID: f036_client
Revises: f035_team_enh
Create Date: 2026-02-11

- user.phone: phone number for clients (nullable)
- buyer_request.client_offers_commission: boolean if client offers commission
- buyer_request.client_commission_value: commission value string (e.g., "3%" or "500 €")
- buyer_request.client_no_commission: boolean if client explicitly says no commission
- buyer_request.view_count: number of views for client requests
"""
from alembic import op
import sqlalchemy as sa


revision = "f036_client"
down_revision = "f035_team_enh"
branch_labels = None
depends_on = None


def upgrade():
    # Add phone field to user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(length=32), nullable=True))
    
    # Add client commission fields to buyer_request table
    # For PostgreSQL, use sa.false() and sa.text() for server defaults
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("client_offers_commission", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("client_commission_value", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("client_no_commission", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
    
    # Update posted_by_role to allow 'client' (it's already String(20), so no schema change needed)
    # Just ensure existing records are set correctly (they should already be 'agent' from f007)


def downgrade():
    # Remove client commission fields from buyer_request
    with op.batch_alter_table("buyer_request", schema=None) as batch_op:
        batch_op.drop_column("view_count")
        batch_op.drop_column("client_no_commission")
        batch_op.drop_column("client_commission_value")
        batch_op.drop_column("client_offers_commission")
    
    # Remove phone field from user
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("phone")
