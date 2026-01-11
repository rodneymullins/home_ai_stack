#!/bin/bash
# Automated Media Organizer - Cron Job
# Add to crontab: */15 * * * * /home/rod/organize_media_cron.sh

LOGFILE="/var/log/media_organizer.log"

echo "$(date): Running media organizer..." >> "$LOGFILE"

# Run organizer
python3 /home/rod/organize_media.py >> "$LOGFILE" 2>&1

# Notify Jellyfin to scan library (if running)
if pgrep -x "jellyfin" > /dev/null; then
    echo "$(date): Triggering Jellyfin library scan..." >> "$LOGFILE"
    # Jellyfin will auto-detect changes, or you can trigger via API
fi

echo "$(date): Media organizer complete" >> "$LOGFILE"
