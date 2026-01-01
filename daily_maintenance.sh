#!/bin/bash
# Automated casino data maintenance script
# Add to crontab: 0 2 * * * /home/rod/home_ai_stack/daily_maintenance.sh

cd /home/rod/home_ai_stack

echo "$(date): Starting daily casino data maintenance" >> /home/rod/home_ai_stack/maintenance.log

# Daily: Refresh slot inventory from casino
echo "$(date): Refreshing slot inventory..." >> /home/rod/home_ai_stack/maintenance.log
/home/rod/home_ai_stack/venv/bin/python3 scrape_slot_inventory.py >> /home/rod/home_ai_stack/maintenance.log 2>&1

# Daily: Update URComped community data
echo "$(date): Updating URComped data..." >> /home/rod/home_ai_stack/maintenance.log
/home/rod/home_ai_stack/venv/bin/python3 scrape_urcomped.py >> /home/rod/home_ai_stack/maintenance.log 2>&1

echo "$(date): Daily maintenance complete" >> /home/rod/home_ai_stack/maintenance.log
echo "----------------------------------------" >> /home/rod/home_ai_stack/maintenance.log
