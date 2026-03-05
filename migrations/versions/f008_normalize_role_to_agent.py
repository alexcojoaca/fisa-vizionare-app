"""Normalize all users to role='agent' (remove utilizator role).

Revision ID: f008_normalize_role
Revises: f007_contact
Create Date: 2026-02-06

- Update all users: SET role='agent' WHERE role IS NULL OR role <> 'agent'
- Update all buyer_request.posted_by_role: SET posted_by_role='agent' WHERE posted_by_role <> 'agent'
"""
from alembic import op
import sqlalchemy as sa


revision = 'f008_normalize_role'
down_revision = 'f007_contact'
branch_labels = None
depends_on = None


def upgrade():
    # Normalize all users to 'agent'
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE \"user\" SET role = 'agent' WHERE role IS NULL OR role <> 'agent'"
    ))
    
    # Normalize all buyer_request.posted_by_role to 'agent'
    conn.execute(sa.text(
        "UPDATE buyer_request SET posted_by_role = 'agent' WHERE posted_by_role IS NOT NULL AND posted_by_role <> 'agent'"
    ))


def downgrade():
    # Cannot safely downgrade - would need to know original roles
    # Leave as-is (all users remain 'agent')
    pass
