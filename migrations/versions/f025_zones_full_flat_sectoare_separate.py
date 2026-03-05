"""Toate zonele ca nume simple (fără 'Sector X - '). Sectoarele ca intrări separate bifabile.

Revision ID: f025_zones_full
Revises: f024_price_negotiable
Create Date: 2026-02-08

- Normalizează zone existente: name = doar numele (fără prefix 'Sector N - ' / 'Ilfov - ')
- group = 'Sectoare' pentru Sector 1..6 și Ultracentral, altfel 'Zone'
- Inserează toate zonele lipsă din listă (cartiere + Sectoare separate)
- Nu mai legăm cartierele de sector; sectoarele sunt alese separat ca zone.
"""
from alembic import op
import sqlalchemy as sa


revision = "f025_zones_full"
down_revision = "f024_price_negotiable"
branch_labels = None
depends_on = None


# Sectoare ca intrări separate (bifabile independent)
SECTORI = ["Sector 1", "Sector 2", "Sector 3", "Sector 4", "Sector 5", "Sector 6", "Ultracentral"]

# Toate zonele/cartierele (nume simple, fără apartenență la sector)
ZONE_NUME = [
    "Aviatorilor", "Aviației", "Băneasa", "Bucureștii Noi", "Chitila", "Clăbucet", "Domenii", "Dorobanți",
    "Floreasca", "Gara de Nord", "Grivița", "Herăstrău", "Jiului", "Kiseleff", "Nordului", "Pajura", "Pipera",
    "Primăverii", "Sisești", "Străulești", "Turda", "Victoriei",
    "Andronache", "Baicului", "Colentina", "Dacia", "Doamna Ghica", "Ferdinand", "Floreasca (parțial)", "Fundeni",
    "Iancului", "Ion Creangă", "Lizeanu", "Moșilor", "Obor", "Pantelimon", "Pache Protopopescu", "Ștefan cel Mare",
    "Tei", "Vatra Luminoasă",
    "Baba Novac", "Balta Albă", "Basarabia", "Calea Călărașilor", "Cățelu", "Centrul Civic", "Costin Georgian",
    "Dristor", "Dudești", "Fizicienilor", "Hala Traian", "Muncii", "Nicolae Grigorescu", "Ozana",
    "Pallady (Theodor Pallady)", "Sălăjan", "Titan", "Unirii (parțial)", "Vitan", "Vitan Mall",
    "Apărătorii Patriei", "Berceni", "Brâncoveanu", "Cantemir", "Eroii Revoluției", "Giurgiului", "Metalurgiei",
    "Olteniței", "Parcul Carol", "Piața Sudului", "Progresul", "Șerban Vodă", "Tineretului", "Văcărești",
    "13 Septembrie", "Alexandriei", "Antiaeriană", "Cotroceni (parțial)", "Drumul Sării", "Ferentari", "Ghencea (parțial)",
    "Izvor", "Liberty Center", "Panduri", "Rahova", "Sebastian", "Trafic Greu", "Uranus", "Viilor",
    "Apusului", "Crângași", "Drumul Taberei", "Giulești", "Gorjului", "Grozăvești", "Lujerului", "Militari",
    "Moinesti", "Politehnica", "Regie", "Uverturii", "Valea Ialomiței", "Valea Oltului", "Virtuții",
    "Amzei", "Armenească", "Batiștei", "Brezoianu", "Calea Victoriei", "Centrul Istoric (Lipscani)", "Cișmigiu",
    "Cotroceni", "Grădina Icoanei", "Kogălniceanu", "Lahovari", "Magheru", "Piața Romană", "Piața Universității",
    "Piața Victoriei", "Sala Palatului", "Știrbei Vodă", "Take Ionescu", "Universitate",
]


def upgrade():
    conn = op.get_bind()

    # 1) Normalizează nume: new_name = partea după " - "; dacă duplicate, păstrăm un id și redirecționăm referințele
    rows = conn.execute(sa.text("SELECT id, name FROM zone")).fetchall()
    by_short = {}  # new_name -> [id, ...]
    for (zid, name) in rows:
        new_name = (name.split(" - ", 1)[-1].strip() if (name and " - " in name) else name) or name
        if not new_name:
            continue
        by_short.setdefault(new_name, []).append(zid)

    for new_name, ids in by_short.items():
        if len(ids) == 1:
            conn.execute(sa.text('UPDATE zone SET name = :n WHERE id = :id'), {"n": new_name, "id": ids[0]})
        else:
            keeper, dupes = ids[0], ids[1:]
            conn.execute(sa.text('UPDATE zone SET name = :n WHERE id = :id'), {"n": new_name, "id": keeper})
            for old_id in dupes:
                # Ștergem rândurile care ar duplica (request_id, zone_id) după merge, apoi redirecționăm restul
                conn.execute(
                    sa.text(
                        "DELETE FROM request_zones WHERE zone_id = :o AND request_id IN (SELECT request_id FROM request_zones WHERE zone_id = :k)"
                    ),
                    {"k": keeper, "o": old_id},
                )
                conn.execute(sa.text("UPDATE request_zones SET zone_id = :k WHERE zone_id = :o"), {"k": keeper, "o": old_id})
                conn.execute(
                    sa.text(
                        "DELETE FROM offer_zones WHERE zone_id = :o AND offer_id IN (SELECT offer_id FROM offer_zones WHERE zone_id = :k)"
                    ),
                    {"k": keeper, "o": old_id},
                )
                conn.execute(sa.text("UPDATE offer_zones SET zone_id = :k WHERE zone_id = :o"), {"k": keeper, "o": old_id})
                conn.execute(sa.text("DELETE FROM zone WHERE id = :id"), {"id": old_id})

    # 2) Setează group: 'Sectoare' pentru Sector 1..6 și Ultracentral, restul 'Zone'
    conn.execute(sa.text('UPDATE zone SET "group" = \'Zone\''))
    for s in SECTORI:
        conn.execute(sa.text('UPDATE zone SET "group" = \'Sectoare\' WHERE name = :n'), {"n": s})

    # 3) Inserează sectoarele ca zone separate dacă lipsesc
    r = conn.execute(sa.text("SELECT COALESCE(MAX(id), 0) FROM zone"))
    next_id = (r.scalar() or 0) + 1
    for name in SECTORI:
        existing = conn.execute(sa.text("SELECT 1 FROM zone WHERE name = :n"), {"n": name}).scalar()
        if not existing:
            conn.execute(
                sa.text('INSERT INTO zone (id, "group", subgroup, name) VALUES (:id, \'Sectoare\', NULL, :name)'),
                {"id": next_id, "name": name},
            )
            next_id += 1

    # 4) Inserează toate cartierele/zonele din listă care lipsesc
    existing = {row[0] for row in conn.execute(sa.text("SELECT name FROM zone")).fetchall()}
    for name in ZONE_NUME:
        if name in existing:
            continue
        try:
            conn.execute(
                sa.text('INSERT INTO zone (id, "group", subgroup, name) VALUES (:id, \'Zone\', NULL, :name)'),
                {"id": next_id, "name": name},
            )
            next_id += 1
            existing.add(name)
        except Exception:
            pass


def downgrade():
    # Nu eliminăm zonele adăugate (ar strica request_zones/offer_zones). Doar documentăm.
    pass
