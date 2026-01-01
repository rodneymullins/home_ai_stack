#!/bin/bash
# Casino Analytics Backup Script
# Backs up the 'jackpots' table from the 'postgres' database
# Retains backups for 30 days.

BACKUP_DIR="/home/rod/backups/jackpots"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="$BACKUP_DIR/jackpots_$TIMESTAMP.sql"

echo "🎰 Starting Backup: $TIMESTAMP"

# Dump specific table 'jackpots'
# Assuming 'rod' user has peer access or .pgpass setup
if pg_dump -U rod -d postgres -t jackpots -f "$FILENAME"; then
    echo "✅ Backup Successful: $FILENAME"
    SIZE=$(du -h "$FILENAME" | cut -f1)
    echo "📦 Size: $SIZE"
    
    # Retention Policy: Delete files older than 30 days
    echo "🧹 Cleaning up old backups (>30 days)..."
    find "$BACKUP_DIR" -name "jackpots_*.sql" -mtime +30 -print -delete
    
    echo "✨ Done."
    exit 0
else
    echo "❌ Backup Failed!"
    rm -f "$FILENAME" # Remove partial file
    exit 1
fi
