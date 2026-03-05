"""create request_zones many-to-many table

Revision ID: f004_request_zones
Revises: f003_buyer_request
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'f004_request_zones'
down_revision = 'f003_buyer_request'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'request_zones',
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('zone_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['buyer_request.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['zone_id'], ['zone.id'], ),
        sa.PrimaryKeyConstraint('request_id', 'zone_id'),
    )
    with op.batch_alter_table('request_zones', schema=None) as batch_op:
        batch_op.create_index('ix_request_zones_zone_request', ['zone_id', 'request_id'], unique=False)


def downgrade():
    with op.batch_alter_table('request_zones', schema=None) as batch_op:
        batch_op.drop_index('ix_request_zones_zone_request')
    op.drop_table('request_zones')
