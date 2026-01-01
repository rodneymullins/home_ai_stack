#!/usr/bin/env python3
"""
Database Connection Pool - Thread-safe PostgreSQL connection pooling
Provides significant performance improvement by reusing connections.
Includes PooledConnection wrapper for transparent pool management.
"""

import psycopg2
from psycopg2 import pool
import threading
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'database': 'postgres',
    'user': 'rod'
}

# Global connection pool
_connection_pool = None
_pool_lock = threading.Lock()

class PooledConnection:
    """
    Wrapper for psycopg2 connection that returns to pool instead of closing.
    Allows drop-in replacement for standard connections.
    """
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        self._closed = False
    
    def __getattr__(self, name):
        # Delegate everything to the underlying connection
        return getattr(self._conn, name)
    
    def close(self):
        """Return connection to pool instead of closing it"""
        if not self._closed and self._conn and self._pool:
            try:
                self._pool.putconn(self._conn)
            except Exception as e:
                logger.error(f"❌ Failed to return connection to pool: {e}")
                # Try to close physically if pool return fails
                try:
                    self._conn.close()
                except:
                    pass
            finally:
                self._closed = True
                self._conn = None
                self._pool = None

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Delegate transaction management to underlying connection
        if self._conn:
            return self._conn.__exit__(exc_type, exc_val, exc_tb)

def init_connection_pool(minconn=2, maxconn=20):
    global _connection_pool
    with _pool_lock:
        if _connection_pool is None:
            try:
                _connection_pool = pool.ThreadedConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    **DB_CONFIG
                )
                logger.info(f"✅ Connection pool initialized (min={minconn}, max={maxconn})")
            except Exception as e:
                logger.error(f"❌ Failed to initialize connection pool: {e}")
                raise
    return _connection_pool

def get_connection_pool():
    if _connection_pool is None:
        return init_connection_pool()
    return _connection_pool

def get_raw_connection():
    """Get raw connection from pool (internal use)"""
    try:
        return get_connection_pool().getconn()
    except Exception as e:
        logger.error(f"❌ Failed to get connection from pool: {e}")
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as fallback_error:
            logger.error(f"❌ Fallback connection also failed: {fallback_error}")
            return None

def get_db_connection():
    """
    Get a pooled connection wrapper.
    Calling .close() on this object returns it to the pool.
    """
    conn = get_raw_connection()
    if conn:
        # Check if we got a raw psycopg2 connection (fallback) or pool connection
        # If it came from pool, current ThreadedConnectionPool implementation returns raw connection
        # We wrap it to handle close() -> putconn()
        return PooledConnection(conn, get_connection_pool())
    return None

def close_all_connections():
    global _connection_pool
    with _pool_lock:
        if _connection_pool:
            try:
                _connection_pool.closeall()
                logger.info("✅ All pool connections closed")
                _connection_pool = None
            except Exception as e:
                logger.error(f"❌ Error closing pool connections: {e}")

# Initialize (safe to rely on module import for this singleton in this context)
try:
    init_connection_pool()
except Exception:
    pass
