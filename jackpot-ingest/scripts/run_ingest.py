#!/usr/bin/env python3
"""CLI runner for ingestion"""
import sys
sys.path.insert(0, '/home/rod/jackpot-ingest')

from app.ingest import run_ingest

if __name__ == "__main__":
    result = run_ingest()
    print(result)
