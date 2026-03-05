"""create buyer_request table (marketplace cereri)

Revision ID: f003_buyer_request
Revises: f002_zone
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'f003_buyer_request'
down_revision = 'f002_zone'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'buyer_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(length=20), nullable=False),
        sa.Column('property_type', sa.String(length=40), nullable=False),
        sa.Column('budget_min', sa.Integer(), nullable=True),
        sa.Column('budget_max', sa.Integer(), nullable=True),
        sa.Column('rooms', sa.Integer(), nullable=True),
        sa.Column('year_min', sa.Integer(), nullable=True),
        sa.Column('year_max', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('urgent', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('buyer_request', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_buyer_request_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_buyer_request_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_buyer_request_type_prop_urgent', ['request_type', 'property_type', 'urgent'], unique=False)


def downgrade():
    with op.batch_alter_table('buyer_request', schema=None) as batch_op:
        batch_op.drop_index('ix_buyer_request_type_prop_urgent')
        batch_op.drop_index(batch_op.f('ix_buyer_request_created_at'))
        batch_op.drop_index(batch_op.f('ix_buyer_request_user_id'))
    op.drop_table('buyer_request')
