"""create zone table and seed Bucharest zones

Revision ID: f002_zone
Revises: f001_user_role
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'f002_zone'
down_revision = 'f001_user_role'
branch_labels = None
depends_on = None


# Bucharest sectors + Ilfov, representative zone names
ZONES_DATA = [
    ("Sector 1", None, "Aviației"),
    ("Sector 1", None, "Băneasa"),
    ("Sector 1", None, "Primăverii"),
    ("Sector 1", None, "Floreasca"),
    ("Sector 1", None, "Pipera"),
    ("Sector 1", None, "Tei"),
    ("Sector 1", None, "Dristor"),
    ("Sector 2", None, "Pantelimon"),
    ("Sector 2", None, "Colentina"),
    ("Sector 2", None, "Obor"),
    ("Sector 2", None, "Iancului"),
    ("Sector 2", None, "Titan"),
    ("Sector 3", None, "Dristor"),
    ("Sector 3", None, "Titan"),
    ("Sector 3", None, "Vitan"),
    ("Sector 3", None, "Unirii"),
    ("Sector 4", None, "Berceni"),
    ("Sector 4", None, "Olteniței"),
    ("Sector 4", None, "Tineretului"),
    ("Sector 5", None, "Rahova"),
    ("Sector 5", None, "Cotroceni"),
    ("Sector 5", None, "Eroii Revoluției"),
    ("Sector 6", None, "Militari"),
    ("Sector 6", None, "Crângași"),
    ("Sector 6", None, "Grozăvești"),
    ("Ilfov", None, "Buftea"),
    ("Ilfov", None, "Otopeni"),
    ("Ilfov", None, "Popești-Leordeni"),
    ("Ilfov", None, "Voluntari"),
    ("Ilfov", None, "Măgurele"),
    ("Ilfov", None, "Chitila"),
]


def upgrade():
    op.create_table(
        'zone',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group', sa.String(length=80), nullable=True),
        sa.Column('subgroup', sa.String(length=80), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('zone', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_zone_name'), ['name'], unique=True)

    conn = op.get_bind()
    # Seed zones (avoid duplicates by name)
    for i, (group, subgroup, name) in enumerate(ZONES_DATA, start=1):
        display_name = f"{group} - {name}" if group else name
        conn.execute(
            sa.text(
                "INSERT INTO zone (id, \"group\", subgroup, name) VALUES (:id, :grp, :sub, :name)"
            ),
            {"id": i, "grp": group, "sub": subgroup, "name": display_name},
        )
def downgrade():
    with op.batch_alter_table('zone', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_zone_name'))
    op.drop_table('zone')
