#!/bin/bash
# Script de start pentru Railway
set -e

# Rulează migrații dacă e necesar
cd "$(dirname "$0")" || exit 1
flask db upgrade || echo "Migrații skip (poate fi ok)"

# Pornește aplicația
exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120
