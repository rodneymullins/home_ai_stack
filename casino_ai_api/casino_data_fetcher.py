"""
Casino Database Connector
Fetches real slot machine data from Gandalf's PostgreSQL database
"""

import psycopg2
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Database config (matching existing pool config)
DB_CONFIG = {
    'database': 'postgres',
    'user': 'rod',
    'host': '192.168.1.211'
}


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)


def fetch_slot_machines(limit: int = 100, denomination: Optional[str] = None) -> List[Dict]:
    """
    Fetch slot machine data from casino database
    
    Args:
        limit: Maximum number of machines to return
        denomination: Filter by denomination (e.g., '$0.01', '$1.00')
    
    Returns:
        List of slot machine dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            machine_name,
            manufacturer,
            denomination,
            type,
            volatility,
            location_code,
            photo_url,
            map_url,
            last_updated
        FROM slot_machines
        WHERE 1=1
    """
    
    params = []
    if denomination is not None:
        query += " AND denomination = %s"
        params.append(denomination)
    
    query += " ORDER BY machine_name LIMIT %s"
    params.append(limit)
    
    cursor.execute(query, params)
    
    columns = [desc[0] for desc in cursor.description]
    machines = []
    
    for row in cursor.fetchall():
        machine = dict(zip(columns, row))
        machines.append(machine)
    
    cursor.close()
    conn.close()
    
    return machines


def fetch_jackpot_history(machine_name: Optional[str] = None, days: int = 30) -> List[Dict]:
    """
    Fetch recent jackpot history
    
    Args:
        machine_name: Specific machine name (optional)
        days: Number of days to look back
    
    Returns:
        List of jackpot records
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            machine_name AS machine_id,
            machine_name,
            amount,
            date_won,
            location,
            scraped_at
        FROM jackpots
        WHERE date_won >= %s
    """
    
    params = [datetime.now() - timedelta(days=days)]
    
    if machine_name:
        query += " AND machine_name = %s"
        params.append(machine_name)
    
    query += " ORDER BY date_won DESC LIMIT 100"
    
    cursor.execute(query, params)
    
    columns = [desc[0] for desc in cursor.description]
    jackpots = []
    
    for row in cursor.fetchall():
        jackpot = dict(zip(columns, row))
        jackpots.append(jackpot)
    
    cursor.close()
    conn.close()
    
    return jackpots


def fetch_multi_casino_data(limit: int = 50) -> List[Dict]:
    """
    Fetch multi-casino jackpot data for comparative analysis
    
    Args:
        limit: Maximum number of records
    
    Returns:
        List of multi-casino jackpot records
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            casino,
            machine_name,
            amount,
            date_text,
            source_url,
            scraped_at
        FROM multi_casino_jackpots
        ORDER BY scraped_at DESC
        LIMIT %s
    """
    
    cursor.execute(query, [limit])
    
    columns = [desc[0] for desc in cursor.description]
    data = []
    
    for row in cursor.fetchall():
        record = dict(zip(columns, row))
        data.append(record)
    
    cursor.close()
    conn.close()
    
    return data


def get_denomination_breakdown() -> List[Dict]:
    """Get slot machine count by denomination"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT denomination, COUNT(*) as count
        FROM slot_machines
        GROUP BY denomination
        ORDER BY count DESC
    """)
    
    results = [{'denomination': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return results


def get_manufacturer_breakdown() -> List[Dict]:
    """Get slot machine count by manufacturer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT manufacturer, COUNT(*) as count
        FROM slot_machines
        WHERE manufacturer IS NOT NULL AND manufacturer != ''
        GROUP BY manufacturer
        ORDER BY count DESC
    """)
    
    results = [{'manufacturer': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return results
