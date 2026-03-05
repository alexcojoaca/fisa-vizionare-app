"""add task table (To-Do for agents)

Revision ID: b8e4a1c2d5f3
Revises: 23d491d61f3f
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8e4a1c2d5f3'
down_revision = '23d491d61f3f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('due_time', sa.Time(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('tags', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    )
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.create_index('ix_task_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_task_user_status', ['user_id', 'status'], unique=False)
        batch_op.create_index('ix_task_status', ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_index('ix_task_status')
        batch_op.drop_index('ix_task_user_status')
        batch_op.drop_index('ix_task_user_id')
    op.drop_table('task')
