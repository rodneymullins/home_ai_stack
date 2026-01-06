#!/usr/bin/env python3
"""
Fellowship Analytics - Usage tracking and reporting
Tracks model usage, response times, failover events across The Fellowship.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FellowshipAnalytics:
    """Track and analyze AI usage across The Fellowship."""
    
    def __init__(self, db_path="~/fellowship_logs/analytics.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize analytics database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Model usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                endpoint TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_length INTEGER,
                response_time_ms INTEGER,
                success BOOLEAN,
                error_message TEXT
            )
        ''')
        
        # Failover events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failover_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                from_endpoint TEXT NOT NULL,
                to_endpoint TEXT NOT NULL,
                reason TEXT,
                model TEXT
            )
        ''')
        
        # Endpoint health table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                endpoint TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time_ms INTEGER,
                models_available INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Analytics database initialized: {self.db_path}")
    
    def log_usage(self, endpoint, model, prompt_length=0, response_time=0, success=True, error=None):
        """Log model usage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO model_usage 
            (endpoint, model, prompt_length, response_time_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (endpoint, model, prompt_length, response_time, success, error))
        conn.commit()
        conn.close()
    
    def log_failover(self, from_endpoint, to_endpoint, reason, model=None):
        """Log failover event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO failover_events 
            (from_endpoint, to_endpoint, reason, model)
            VALUES (?, ?, ?, ?)
        ''', (from_endpoint, to_endpoint, reason, model))
        conn.commit()
        conn.close()
        logger.warning(f"🔄 Failover: {from_endpoint} → {to_endpoint} ({reason})")
    
    def log_health(self, endpoint, status, response_time=0, models_count=0):
        """Log health check."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO health_checks 
            (endpoint, status, response_time_ms, models_available)
            VALUES (?, ?, ?, ?)
        ''', (endpoint, status, response_time, models_count))
        conn.commit()
        conn.close()
    
    def get_usage_stats(self, days=7):
        """Get usage statistics for the past N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(days=days)
        
        # Total requests
        cursor.execute('''
            SELECT COUNT(*) FROM model_usage 
            WHERE timestamp >= ?
        ''', (since,))
        total_requests = cursor.fetchone()[0]
        
        # Requests by endpoint
        cursor.execute('''
            SELECT endpoint, COUNT(*) as count 
            FROM model_usage 
            WHERE timestamp >= ?
            GROUP BY endpoint
        ''', (since,))
        by_endpoint = dict(cursor.fetchall())
        
        # Requests by model
        cursor.execute('''
            SELECT model, COUNT(*) as count 
            FROM model_usage 
            WHERE timestamp >= ?
            GROUP BY model
            ORDER BY count DESC
            LIMIT 10
        ''', (since,))
        top_models = cursor.fetchall()
        
        # Average response times
        cursor.execute('''
            SELECT endpoint, AVG(response_time_ms) as avg_time
            FROM model_usage 
            WHERE timestamp >= ? AND success = 1
            GROUP BY endpoint
        ''', (since,))
        avg_times = dict(cursor.fetchall())
        
        # Failover count
        cursor.execute('''
            SELECT COUNT(*) FROM failover_events 
            WHERE timestamp >= ?
        ''', (since,))
        failovers = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'period_days': days,
            'total_requests': total_requests,
            'by_endpoint': by_endpoint,
            'top_models': top_models,
            'avg_response_times': avg_times,
            'failover_count': failovers
        }
    
    def generate_report(self, days=7):
        """Generate usage report."""
        stats = self.get_usage_stats(days)
        
        report = f"""
🏰 The Fellowship Analytics Report
{'=' * 50}
Period: Last {days} days

📊 Overall Statistics:
  • Total Requests: {stats['total_requests']}
  • Failover Events: {stats['failover_count']}
  • Failover Rate: {(stats['failover_count']/stats['total_requests']*100 if stats['total_requests'] > 0 else 0):.1f}%

🖥️  Usage by Endpoint:
"""
        for endpoint, count in stats['by_endpoint'].items():
            pct = count / stats['total_requests'] * 100 if stats['total_requests'] > 0 else 0
            report += f"  • {endpoint}: {count} ({pct:.1f}%)\n"
        
        report += f"\n🤖 Top Models:\n"
        for model, count in stats['top_models']:
            pct = count / stats['total_requests'] * 100 if stats['total_requests'] > 0 else 0
            report += f"  • {model}: {count} ({pct:.1f}%)\n"
        
        report += f"\n⚡ Average Response Times:\n"
        for endpoint, avg_time in stats['avg_response_times'].items():
            report += f"  • {endpoint}: {avg_time:.0f}ms\n"
        
        report += f"\n{'=' * 50}\n"
        return report


def main():
    """Demo analytics functionality."""
    analytics = FellowshipAnalytics()
    
    # Show recent stats
    print(analytics.generate_report(days=30))


if __name__ == '__main__':
    main()
