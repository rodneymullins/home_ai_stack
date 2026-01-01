#!/bin/bash
# Heimdall to Thor Nightly Backup Script
# Backs up critical data from Heimdall to Thor's RAID0

# Configuration
BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_TIME=$(date +%H:%M:%S)
LOG_FILE="/var/log/heimdall-backup.log"
BACKUP_DEST="/media/thor/backups/heimdall"
RETENTION_DAYS=30

# Directories to backup
BACKUP_SOURCES=(
    "/home/rod/jellyfin/config"
    "/home/rod/jellyseerr/config"
    "/home/rod/sonarr/config"
    "/home/rod/radarr/config"
    "/home/rod/prowlarr/config"
    "/home/rod/qbittorrent/config"
    "/var/www/homer"
)

# Add Nextcloud when installed
if [ -d "/mnt/internal-hdd/nextcloud/data" ]; then
    BACKUP_SOURCES+=("/mnt/internal-hdd/nextcloud/data")
fi
if [ -d "/mnt/internal-hdd/nextcloud/db" ]; then
    BACKUP_SOURCES+=("/mnt/internal-hdd/nextcloud/db")
fi


# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Start backup
log "========================================="
log "Starting Heimdall backup to Thor"
log "========================================="

# Create backup destination if it doesn't exist
if [ ! -d "$BACKUP_DEST" ]; then
    log "Creating backup destination: $BACKUP_DEST"
    mkdir -p "$BACKUP_DEST"
fi

# Backup each source
TOTAL_SIZE=0
SUCCESS_COUNT=0
FAIL_COUNT=0

for SOURCE in "${BACKUP_SOURCES[@]}"; do
    if [ ! -e "$SOURCE" ]; then
        log "WARNING: Source does not exist: $SOURCE (skipping)"
        continue
    fi
    
    # Get basename for destination folder
    BASENAME=$(basename "$SOURCE")
    PARENT=$(basename $(dirname "$SOURCE"))
    DEST_DIR="$BACKUP_DEST/$PARENT-$BASENAME"
    
    log "Backing up: $SOURCE -> $DEST_DIR"
    
    # Use rsync for incremental backup
    rsync -avz --delete \
        --exclude='*.log' \
        --exclude='cache/*' \
        --exclude='tmp/*' \
        "$SOURCE/" "$DEST_DIR/" >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        SIZE=$(du -sh "$DEST_DIR" | cut -f1)
        log "✅ Success: $SOURCE ($SIZE)"
        ((SUCCESS_COUNT++))
    else
        log "❌ Failed: $SOURCE"
        ((FAIL_COUNT++))
    fi
done

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DEST" | cut -f1)

# Clean up old backups (optional - if using dated backups)
log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DEST" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null

# Summary
log "========================================="
log "Backup Summary:"
log "  Successful: $SUCCESS_COUNT"
log "  Failed: $FAIL_COUNT"
log "  Total Size: $TOTAL_SIZE"
log "  Destination: $BACKUP_DEST"
log "========================================="

# Send notification if there were failures
if [ $FAIL_COUNT -gt 0 ]; then
    log "⚠️  WARNING: $FAIL_COUNT backup(s) failed!"
    exit 1
else
    log "✅ All backups completed successfully"
    exit 0
fi
