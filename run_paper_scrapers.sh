#!/bin/bash
# Research Paper Scraper Automation
# Run all paper scrapers on a schedule

SCRIPT_DIR="/Users/rod/Antigravity/home_ai_stack/scrapers"
LOG_DIR="/Users/rod/Antigravity/home_ai_stack/logs"
mkdir -p "$LOG_DIR"

echo "$(date): Starting research paper collection" >> "$LOG_DIR/paper_scraper.log"

# ArXiv scraper (most papers)
echo "Running ArXiv scraper..." >> "$LOG_DIR/paper_scraper.log"
cd "$SCRIPT_DIR"
python3 arxiv_scraper.py --limit 50 >> "$LOG_DIR/arxiv.log" 2>&1

# PsyArXiv scraper
echo "Running PsyArXiv scraper..." >> "$LOG_DIR/paper_scraper.log"
python3 psyarxiv_scraper.py --limit 25 >> "$LOG_DIR/psyarxiv.log" 2>&1

# NBER scraper
echo "Running NBER scraper..." >> "$LOG_DIR/paper_scraper.log"
python3 nber_scraper.py --limit 10 >> "$LOG_DIR/nber.log" 2>&1

echo "$(date): Paper collection complete" >> "$LOG_DIR/paper_scraper.log"

# Count papers
PAPER_COUNT=$(ssh rod@192.168.1.211 "psql -U rod -d research_papers -t -c 'SELECT COUNT(*) FROM papers;'" 2>/dev/null | tr -d ' ')
echo "Total papers in database: $PAPER_COUNT" >> "$LOG_DIR/paper_scraper.log"
