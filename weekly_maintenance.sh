#!/bin/bash
# Weekly manufacturer data refresh
# Add to crontab: 0 3 * * 0 /home/rod/home_ai_stack/weekly_maintenance.sh

cd /home/rod/home_ai_stack

echo "$(date): Starting weekly manufacturer data update" >> /home/rod/home_ai_stack/maintenance.log

# Weekly: Update IGT manufacturer specs
echo "$(date): Updating IGT specs..." >> /home/rod/home_ai_stack/maintenance.log
/home/rod/home_ai_stack/venv/bin/python3 scrape_igt_specs.py >> /home/rod/home_ai_stack/maintenance.log 2>&1

# Weekly: Multi-casino comparison
echo "$(date): Running multi-casino aggregation..." >> /home/rod/home_ai_stack/maintenance.log
/home/rod/home_ai_stack/venv/bin/python3 scrape_multi_casino.py >> /home/rod/home_ai_stack/maintenance.log 2>&1

echo "$(date): Weekly maintenance complete" >> /home/rod/home_ai_stack/maintenance.log
echo "========================================" >> /home/rod/home_ai_stack/maintenance.log
