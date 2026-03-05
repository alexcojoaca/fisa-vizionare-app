"""Add contact_phone and posted_by_role to buyer_request.

Revision ID: f007_contact
Revises: f006_collab
Create Date: 2026-02-05

- contact_phone: optional phone, visibility controlled server-side.
- posted_by_role: 'agent' | 'utilizator' snapshot at creation for filtering.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f007_contact'
down_revision = 'f006_collab'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('buyer_request', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_phone', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('posted_by_role', sa.String(length=20), nullable=True))

    # Backfill posted_by_role from user.role (quote "user" for PostgreSQL reserved word)
    conn = op.get_bind()
    conn.execute(sa.text(
        'UPDATE buyer_request SET posted_by_role = (SELECT role FROM "user" WHERE "user".id = buyer_request.user_id)'
    ))


def downgrade():
    with op.batch_alter_table('buyer_request', schema=None) as batch_op:
        batch_op.drop_column('posted_by_role')
        batch_op.drop_column('contact_phone')
