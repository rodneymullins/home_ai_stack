"""Main ingestion orchestrator"""
from decimal import Decimal
from .db import get_conn, upsert_source
from .normalize import fingerprint

from .scrapers.foxwoods import FoxwoodsSlots
from .scrapers.mohegan import MoheganJackpots
from .scrapers.hardrock_tampa import HardRockTampa
from .scrapers.choctaw import ChoctawDurant
from .scrapers.misc import Pechanga, WinStar, HardRockHollywood

SCRAPERS = [
    FoxwoodsSlots(),
    MoheganJackpots(),
    HardRockTampa(),
    ChoctawDurant(),
    Pechanga(),
    WinStar(),
    HardRockHollywood(),
]

def run_ingest():
    """Run ingestion for all casinos"""
    conn = get_conn()
    conn.autocommit = False
    
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ingest_runs DEFAULT VALUES RETURNING id")
            run_id = cur.fetchone()['id']

        inserted = 0
        for s in SCRAPERS:
            try:
                source_id = upsert_source(conn, s.casino, s.property, s.base_url)
                rows = s.fetch()
                
                for row in rows:
                    fp = fingerprint(
                        row.get("source_url") or s.base_url,
                        row.get("posted_date"),
                        Decimal(str(row["amount"])) if row.get("amount") is not None else None,
                        row.get("winner_name"),
                        row.get("game"),
                    )
                    
                    with conn.cursor() as cur:
                        # Insert into multi_casino_jackpots table
                        cur.execute("""
                          INSERT INTO multi_casino_jackpots
                            (casino, machine_name, amount, date_text, source_url, source_id)
                          VALUES (%s, %s, %s, %s, %s, %s)
                          ON CONFLICT DO NOTHING
                        """, (
                            s.casino,
                            row.get("game") or "Unknown",
                            row.get("amount"),
                            str(row.get("posted_date")) if row.get("posted_date") else None,
                            row.get("source_url") or s.base_url,
                            source_id,
                        ))
                        inserted += cur.rowcount
            except Exception as e:
                print(f"{s.casino} error: {e}")
                continue

        with conn.cursor() as cur:
            cur.execute("UPDATE ingest_runs SET status='ok', finished_at=NOW() WHERE id=%s", (run_id,))
        
        conn.commit()
        print(f"✅ Ingestion complete: {inserted} new jackpots")
        return {"status": "ok", "inserted": inserted}
        
    except Exception as e:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ingest_runs SET status='error', error=%s, finished_at=NOW() WHERE id=(SELECT MAX(id) FROM ingest_runs)",
                (str(e),)
            )
        conn.commit()
        print(f"❌ Ingestion failed: {e}")
        raise
    finally:
        conn.close()
