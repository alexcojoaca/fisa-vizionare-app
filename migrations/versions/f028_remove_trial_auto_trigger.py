"""Remove any database triggers that auto-set trial_ends_at on user creation.

Revision ID: f028_remove_trial_trigger
Revises: f027_free_actions
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f028_remove_trial_trigger"
down_revision = "f027_free_actions"
branch_labels = None
depends_on = None


def upgrade():
    """
    Șterge orice trigger care setează automat trial_ends_at la crearea utilizatorului.
    Utilizatorii noi nu mai primesc trial pe zile - doar 3 acțiuni gratuite.
    """
    # Verifică și șterge trigger-uri care ar putea seta trial_ends_at automat
    # Folosim raw SQL pentru a verifica și șterge trigger-uri
    connection = op.get_bind()
    
    # Găsește toate trigger-urile pe tabelul user
    result = connection.execute(sa.text("""
        SELECT tgname 
        FROM pg_trigger 
        WHERE tgrelid = 'user'::regclass 
        AND tgname NOT LIKE 'RI_%'  -- exclude foreign key triggers
    """))
    
    triggers_to_check = [row[0] for row in result]
    
    # Șterge trigger-urile care ar putea seta trial_ends_at
    # (numele comune pentru astfel de trigger-uri)
    for trigger_name in triggers_to_check:
        trigger_def = connection.execute(sa.text(f"""
            SELECT pg_get_triggerdef(oid) 
            FROM pg_trigger 
            WHERE tgname = '{trigger_name}'
        """)).scalar()
        
        # Dacă trigger-ul conține "trial_ends_at", îl ștergem
        if trigger_def and 'trial_ends_at' in trigger_def.lower():
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name} ON \"user\""))


def downgrade():
    # Nu recreăm trigger-urile - nu avem nevoie de ele
    pass
