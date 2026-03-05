"""Add request_type and property_type to marketplace_alert.

Revision ID: f013_marketplace_alert_request_property_type
Revises: f012_assistant_reminder_marketplace_alert
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "f013_marketplace_alert_request_property_type"
down_revision = "f012_assistant_reminder_marketplace_alert"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("marketplace_alert", schema=None) as batch_op:
        batch_op.add_column(sa.Column("request_type", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("property_type", sa.String(20), nullable=True))


def downgrade():
    with op.batch_alter_table("marketplace_alert", schema=None) as batch_op:
        batch_op.drop_column("property_type")
        batch_op.drop_column("request_type")
