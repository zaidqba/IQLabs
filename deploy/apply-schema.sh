#!/usr/bin/env bash
# ─── Apply IQ-RAD schema to Ionetix3/SQLEXPRESS ────────────────────────────────
# Run from iqlabsserver1 after editing .env
# Usage: bash apply-schema.sh
set -euo pipefail
cd "$(dirname "$0")"

source .env

# Parse connection info from DATABASE_URL
# Format: mssql+aioodbc://USER:PASS@SERVER/DB?...
DB_SERVER=$(echo "$DATABASE_URL" | grep -oP '(?<=@)[^/?]+')
DB_NAME=$(echo "$DATABASE_URL" | grep -oP '(?<=/)[^?]+' | head -1)
DB_USER=$(echo "$DATABASE_URL" | grep -oP '(?<=//)[^:]+')
DB_PASS=$(echo "$DATABASE_URL" | grep -oP '(?<=://[^:]{1,50}:)[^@]+')

SQLCMD=${SQLCMD_PATH:-/opt/mssql-tools18/bin/sqlcmd}

echo "[schema] Server:   $DB_SERVER"
echo "[schema] Database: $DB_NAME"
echo "[schema] User:     $DB_USER"
echo ""

echo "[schema] Creating database IQ_RAD if not exists..."
$SQLCMD -S "$DB_SERVER" -U "$DB_USER" -P "$DB_PASS" -C \
    -Q "IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name='IQ_RAD') CREATE DATABASE IQ_RAD"

echo "[schema] Applying schema scripts..."
SCHEMA_DIR="../database/schema"
for f in "$SCHEMA_DIR"/0*.sql; do
    echo "[schema]   → $(basename $f)"
    $SQLCMD -S "$DB_SERVER" -U "$DB_USER" -P "$DB_PASS" -C -d IQ_RAD -i "$f"
done

echo "[schema] Done. IQ_RAD database is ready."
