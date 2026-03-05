"""Extend zones: Sector 1..6 + Ilfov taxonomy, full neighborhoods

Revision ID: f005_zones
Revises: f004_request_zones
Create Date: 2026-02-05

Adds zones for Bucharest sectors and Ilfov. Existing zones (1-28) are unchanged.
New zones get IDs after current max. Group order: Sector 1..6, Ilfov.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f005_zones'
down_revision = 'f004_request_zones'
branch_labels = None
depends_on = None


# (group, name) - name must be unique. Format "Sector N - Cartier" or "Ilfov - Localitate"
# Existing f002 seed already has 28 zones. We add more; duplicates by (group, name) skipped by using unique names.
NEW_ZONES = [
    # Sector 1
    ("Sector 1", "Sector 1 - Aviatorilor"),
    ("Sector 1", "Sector 1 - Dorobanți"),
    ("Sector 1", "Sector 1 - Herăstrău"),
    ("Sector 1", "Sector 1 - Pajura"),
    ("Sector 1", "Sector 1 - Domenii"),
    ("Sector 1", "Sector 1 - Grivița"),
    ("Sector 1", "Sector 1 - Bucureștii Noi"),
    ("Sector 1", "Sector 1 - Damaroaia"),
    ("Sector 1", "Sector 1 - Străulești"),
    ("Sector 1", "Sector 1 - Jiului"),
    # Sector 2 (some already in f002)
    ("Sector 2", "Sector 2 - Ștefan cel Mare"),
    ("Sector 2", "Sector 2 - Fundeni"),
    # Sector 3
    ("Sector 3", "Sector 3 - 1 Decembrie 1918"),
    ("Sector 3", "Sector 3 - Nicolae Grigorescu"),
    ("Sector 3", "Sector 3 - Dudești"),
    # Sector 4
    ("Sector 4", "Sector 4 - Timpuri Noi"),
    ("Sector 4", "Sector 4 - Giurgiului"),
    # Sector 5
    ("Sector 5", "Sector 5 - Ferentari"),
    ("Sector 5", "Sector 5 - 13 Septembrie"),
    ("Sector 5", "Sector 5 - Drumul Sării"),
    # Sector 6
    ("Sector 6", "Sector 6 - Drumul Taberei"),
    ("Sector 6", "Sector 6 - Giulești"),
    ("Sector 6", "Sector 6 - Regie"),
    # Ilfov
    ("Ilfov", "Ilfov - Tunari"),
    ("Ilfov", "Ilfov - Corbeanca"),
    ("Ilfov", "Ilfov - Snagov"),
    ("Ilfov", "Ilfov - Mogoșoaia"),
    ("Ilfov", "Ilfov - Bragadiru"),
    ("Ilfov", "Ilfov - Chiajna"),
    ("Ilfov", "Ilfov - Domnești"),
    ("Ilfov", "Ilfov - Pantelimon (oraș)"),
]


def upgrade():
    conn = op.get_bind()
    # Get current max id (existing seed has 1-28)
    r = conn.execute(sa.text("SELECT COALESCE(MAX(id), 0) FROM zone"))
    next_id = (r.scalar() or 0) + 1
    for group, name in NEW_ZONES:
        try:
            conn.execute(
                sa.text(
                    'INSERT INTO zone (id, "group", subgroup, name) VALUES (:id, :grp, NULL, :name)'
                ),
                {"id": next_id, "grp": group, "name": name},
            )
            next_id += 1
        except Exception:
            # Skip if name already exists (unique constraint)
            pass


def downgrade():
    conn = op.get_bind()
    for _group, name in NEW_ZONES:
        # Remove request_zones that reference this zone, then the zone
        conn.execute(sa.text("DELETE FROM request_zones WHERE zone_id IN (SELECT id FROM zone WHERE name = :name)"), {"name": name})
        conn.execute(sa.text("DELETE FROM zone WHERE name = :name"), {"name": name})
