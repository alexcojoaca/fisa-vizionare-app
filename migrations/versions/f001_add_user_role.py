"""add role to user (marketplace: agent / utilizator)

Revision ID: f001_user_role
Revises: b8e4a1c2d5f3
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'f001_user_role'
down_revision = 'b8e4a1c2d5f3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('role', sa.String(length=20), nullable=False, server_default='agent'))
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_role'), ['role'], unique=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_role'))
    op.drop_column('user', 'role')
