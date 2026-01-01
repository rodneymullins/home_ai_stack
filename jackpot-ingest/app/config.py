"""Configuration for jackpot ingestion"""
import os

class Config:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://rod@localhost:5432/postgres")
    USER_AGENT = os.environ.get("USER_AGENT", "jackpot-ingest/1.0")
    REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "20"))
    PORT = int(os.environ.get("PORT", "8089"))
