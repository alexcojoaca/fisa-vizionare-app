"""Add free_rental_viewing_used and free_sale_viewing_used boolean fields to User.

Revision ID: f029_free_viewing_flags
Revises: f028_remove_trial_trigger
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "f029_free_viewing_flags"
down_revision = "f028_remove_trial_trigger"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("free_rental_viewing_used", sa.Boolean(), nullable=False, server_default="false"))
        batch_op.add_column(sa.Column("free_sale_viewing_used", sa.Boolean(), nullable=False, server_default="false"))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("free_sale_viewing_used")
        batch_op.drop_column("free_rental_viewing_used")
