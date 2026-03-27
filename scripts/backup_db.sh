#!/usr/bin/env bash
# ──────────────────────────────────────────────
# NMK Community Finance — SQLite Backup Script
# ──────────────────────────────────────────────
# Usage:  ./scripts/backup_db.sh
# Cron:   0 2 * * * /path/to/nmk_finance/scripts/backup_db.sh
#
# Keeps the last 30 days of backups and auto-deletes older ones.

set -euo pipefail

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_FILE="${PROJECT_DIR}/db.sqlite3"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETAIN_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if database file exists
if [ ! -f "${DB_FILE}" ]; then
    echo "[BACKUP] ERROR: Database file not found at ${DB_FILE}"
    exit 1
fi

# Create timestamped backup using SQLite's .backup command (safe for concurrent access)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_${TIMESTAMP}.sqlite3"

sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"

echo "[BACKUP] Created: ${BACKUP_FILE}"

# Remove backups older than RETAIN_DAYS
find "${BACKUP_DIR}" -name "db_*.sqlite3" -mtime +${RETAIN_DAYS} -delete

echo "[BACKUP] Cleaned up backups older than ${RETAIN_DAYS} days."
echo "[BACKUP] Done."
