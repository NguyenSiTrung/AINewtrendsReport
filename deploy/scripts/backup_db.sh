#!/usr/bin/env bash
# backup_db.sh — Daily SQLite backup with retention cleanup
# Called by /etc/cron.d/ainews-backup
set -euo pipefail

DB_PATH="${AINEWS_DB_PATH:-/var/lib/ainews/ainews.db}"
BACKUP_DIR="${AINEWS_BACKUP_DIR:-/var/backups/ainews}"
RETENTION_DAYS="${AINEWS_BACKUP_RETENTION_DAYS:-30}"

DATE_STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ainews_${DATE_STAMP}.db"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Perform SQLite online backup
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE}'"
    echo "$(date -Iseconds) Backup created: ${BACKUP_FILE} ($(stat -c%s "$BACKUP_FILE") bytes)"
else
    echo "$(date -Iseconds) ERROR: Database not found at ${DB_PATH}"
    exit 1
fi

# Cleanup old backups beyond retention period
find "$BACKUP_DIR" -name "ainews_*.db" -type f -mtime +${RETENTION_DAYS} -delete
REMAINING=$(find "$BACKUP_DIR" -name "ainews_*.db" -type f | wc -l)
echo "$(date -Iseconds) Retention cleanup done (kept ${REMAINING} backups, max age ${RETENTION_DAYS} days)"
