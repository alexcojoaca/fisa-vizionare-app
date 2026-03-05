"""add_completion_token_to_task

Revision ID: e7afc645651b
Revises: f033_collab
Create Date: 2026-02-10 12:30:32.666567

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7afc645651b'
down_revision = 'f033_collab'
branch_labels = None
depends_on = None


def upgrade():
    # Add completion_token column to task table
    op.add_column('task', sa.Column('completion_token', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_task_completion_token'), 'task', ['completion_token'], unique=True)


def downgrade():
    # Remove completion_token column
    op.drop_index(op.f('ix_task_completion_token'), table_name='task')
    op.drop_column('task', 'completion_token')
