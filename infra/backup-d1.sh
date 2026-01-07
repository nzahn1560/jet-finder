#!/bin/bash
# Backup D1 database script
# Usage: ./backup-d1.sh [database-name]

set -e

DB_NAME="${1:-jetschoolusa-db}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/d1_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "🔄 Backing up D1 database: ${DB_NAME}..."

# Export schema
echo "-- D1 Database Backup" > "${BACKUP_FILE}"
echo "-- Generated: $(date)" >> "${BACKUP_FILE}"
echo "-- Database: ${DB_NAME}" >> "${BACKUP_FILE}"
echo "" >> "${BACKUP_FILE}"

echo "📋 Exporting schema..."
wrangler d1 execute "${DB_NAME}" --command "SELECT sql FROM sqlite_master WHERE type='table'" >> "${BACKUP_FILE}" 2>/dev/null || true

echo "📊 Exporting data..."

# Export each table
TABLES=$(wrangler d1 execute "${DB_NAME}" --command "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" --json | jq -r '.[].name' 2>/dev/null || echo "")

if [ -z "$TABLES" ]; then
    echo "⚠️  No tables found or error reading tables"
else
    for TABLE in $TABLES; do
        echo "  - Exporting table: ${TABLE}"
        echo "" >> "${BACKUP_FILE}"
        echo "-- Table: ${TABLE}" >> "${BACKUP_FILE}"
        wrangler d1 execute "${DB_NAME}" --command ".mode insert ${TABLE}" --command "SELECT * FROM ${TABLE}" >> "${BACKUP_FILE}" 2>/dev/null || true
    done
fi

echo "✅ Backup complete: ${BACKUP_FILE}"
echo "📁 File size: $(du -h "${BACKUP_FILE}" | cut -f1)"

# Optional: Compress backup
if command -v gzip &> /dev/null; then
    echo "🗜️  Compressing backup..."
    gzip "${BACKUP_FILE}"
    echo "✅ Compressed backup: ${BACKUP_FILE}.gz"
fi

