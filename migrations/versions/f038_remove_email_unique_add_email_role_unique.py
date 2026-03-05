"""remove email unique constraint, add unique constraint on (email, role)

Revision ID: f038_email_role_unique
Revises: f037_etaj
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = 'f038_email_role_unique'
down_revision = 'f037_etaj'
branch_labels = None
depends_on = None


def upgrade():
    # Elimină indexul unique existent pe email
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Drop the old unique index
        try:
            batch_op.drop_index('ix_user_email')
        except Exception:
            pass  # Index-ul poate să nu existe sau să aibă alt nume
    
    # Creează index non-unique pe email
    op.create_index('ix_user_email', 'user', ['email'], unique=False)
    
    # Creează constraint unique pe (email, role)
    op.create_unique_constraint('uq_user_email_role', 'user', ['email', 'role'])


def downgrade():
    # Elimină constraint-ul compus
    op.drop_constraint('uq_user_email_role', 'user', type_='unique')
    
    # Elimină indexul non-unique
    op.drop_index('ix_user_email', table_name='user')
    
    # Recreează indexul unique pe email
    op.create_index('ix_user_email', 'user', ['email'], unique=True)
