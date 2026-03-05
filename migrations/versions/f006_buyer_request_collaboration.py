"""Add collaboration_type and commission_percent to buyer_request (PF only).

Revision ID: f006_collab
Revises: f005_zones
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'f006_collab'
down_revision = 'f005_zones'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('buyer_request', schema=None) as batch_op:
        batch_op.add_column(sa.Column('collaboration_type', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('commission_percent', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('buyer_request', schema=None) as batch_op:
        batch_op.drop_column('commission_percent')
        batch_op.drop_column('collaboration_type')
