"""Normalization and fingerprinting"""
import hashlib
from decimal import Decimal
from datetime import date
from typing import Optional

def _norm_text(x: Optional[str]) -> str:
    return (x or "").strip().lower()

def fingerprint(source_url: str, posted_date: Optional[date], amount: Optional[Decimal], 
                winner_name: Optional[str], game: Optional[str]) -> str:
    """Generate unique fingerprint for deduplication"""
    key = "|".join([
        _norm_text(source_url),
        (posted_date.isoformat() if posted_date else ""),
        (str(amount) if amount is not None else ""),
        _norm_text(winner_name),
        _norm_text(game),
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
