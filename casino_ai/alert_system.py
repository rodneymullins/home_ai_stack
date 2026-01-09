"""
Real-Time Hot Machine Alert System

Phase 4: Monitors machines and sends alerts when hot machines detected.
"""
import time
import psycopg2
from datetime import datetime, timedelta
from typing import List, Dict
import json


class HotMachineAlertSystem:
    """
    Real-time alert system for hot slot machines.
    
    Monitors all machines and triggers alerts when:
    - Hot score > 0.8
    - Predicted jackpot < 15 minutes
    - Pattern anomaly detected
    """
    
    def __init__(self, db_config: Dict = None):
        if db_config is None:
            db_config = {
                'host': '192.168.1.211',
                'database': 'postgres',
                'user': 'rod'
            }
        
        self.db_config = db_config
        self.alert_history = []
        self.notified_machines = set()  # Avoid spam
    
    def _get_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(**self.db_config)
    
    def create_alerts_table(self):
        """Create alerts tracking table"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hot_machine_alerts (
                    id SERIAL PRIMARY KEY,
                    machine_id TEXT,
                    alert_time TIMESTAMP DEFAULT NOW(),
                    hot_score REAL,
                    predicted_minutes INT,
                    classification TEXT,
                    recommendation TEXT,
                    user_notified BOOLEAN DEFAULT FALSE,
                    jackpot_occurred BOOLEAN,
                    jackpot_time TIMESTAMP,
                    alert_type TEXT
                )
            """)
            conn.commit()
            print("✅ Alerts table created")
        except Exception as e:
            print(f"Error creating alerts table: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def check_for_hot_machines(self) -> List[Dict]:
        """
        Scan all machines for hot alerts.
        
        Returns list of machines that triggered alerts.
        """
        from casino_ai.ai_integration import CasinoAIEngine
        
        # Initialize AI engine
        try:
            ai_engine = CasinoAIEngine()
        except Exception as e:
            print(f"Error initializing AI engine: {e}")
            return []
        
        # Get list of machines to check (from database)
        machines_to_check = self._get_active_machines()
        
        hot_alerts = []
        
        for machine_id in machines_to_check:
            try:
                # Get AI analysis
                analysis = ai_engine.analyze_machine_complete(machine_id)
                
                # Check alert conditions
                if self._should_alert(analysis):
                    alert = {
                        'machine_id': machine_id,
                        'hot_score': analysis.get('ai_hot_score', 0),
                        'predicted_minutes': analysis.get('ml_predicted_minutes'),
                        'classification': analysis.get('ml_classification'),
                        'recommendation': analysis.get('final_recommendation'),
                        'alert_type': self._get_alert_type(analysis),
                        'timestamp': datetime.now()
                    }
                    
                    hot_alerts.append(alert)
                    
                    # Log to database
                    self._log_alert(alert)
                    
            except Exception as e:
                print(f"Error analyzing {machine_id}: {e}")
                continue
        
        return hot_alerts
    
    def _get_active_machines(self) -> List[str]:
        """Get list of active machines from database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT machine_name 
                FROM jackpots 
                WHERE date_won > NOW() - INTERVAL '7 days'
                LIMIT 50
            """)
            
            machines = [row[0] for row in cursor.fetchall()]
            return machines
        finally:
            conn.close()
    
    def _should_alert(self, analysis: Dict) -> bool:
        """
        Determine if analysis triggers an alert.
        
        Alert conditions:
        1. Hot score > 0.8 (very hot)
        2. Predicted time < 15 min (imminent)
        3. Classification = HOT + high confidence
        """
        # Avoid repeat alerts
        machine_id = analysis.get('machine_id')
        if machine_id in self.notified_machines:
            return False
        
        hot_score = analysis.get('ai_hot_score', 0)
        predicted_min = analysis.get('ml_predicted_minutes', 999)
        classification = analysis.get('ml_classification', '')
        confidence = analysis.get('ai_confidence', 0)
        
        # High hot score
        if hot_score >= 0.8 and confidence >= 0.7:
            return True
        
        # Imminent jackpot
        if predicted_min < 15 and classification == 'HOT':
            return True
        
        # Hot classification with high combined score
        combined = analysis.get('combined_score', 0)
        if classification == 'HOT' and combined >= 0.75:
            return True
        
        return False
    
    def _get_alert_type(self, analysis: Dict) -> str:
        """Determine alert type"""
        hot_score = analysis.get('ai_hot_score', 0)
        predicted_min = analysis.get('ml_predicted_minutes', 999)
        
        if predicted_min < 10:
            return 'IMMINENT_JACKPOT'
        elif hot_score >= 0.85:
            return 'VERY_HOT_MACHINE'
        else:
            return 'HOT_MACHINE'
    
    def _log_alert(self, alert: Dict):
        """Log alert to database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hot_machine_alerts (
                    machine_id, hot_score, predicted_minutes,
                    classification, recommendation, alert_type
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                alert['machine_id'],
                alert['hot_score'],
                alert['predicted_minutes'],
                alert['classification'],
                alert['recommendation'],
                alert['alert_type']
            ))
            conn.commit()
        except Exception as e:
            print(f"Error logging alert: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def send_notification(self, alert: Dict):
        """
        Send notification for alert.
        
        Can be extended to:
        - Browser notification
        - SMS/email
        - Dashboard badge
        - Sound alert
        """
        # Mark as notified
        self.notified_machines.add(alert['machine_id'])
        
        # Print to console (can add other notification methods)
        print(f"\n🔥 HOT MACHINE ALERT!")
        print(f"   Machine: {alert['machine_id']}")
        print(f"   Score: {alert['hot_score']*100:.0f}/100")
        print(f"   Predicted: {alert['predicted_minutes']} min")
        print(f"   Action: {alert['recommendation']}")
        print(f"   Time: {alert['timestamp'].strftime('%H:%M:%S')}")
        print("")
        
        # TODO: Add browser notification API call
        # TODO: Add SMS/email if configured
    
    def run_monitor(self, interval_seconds: int = 120):
        """
        Run continuous monitoring loop.
        
        Args:
            interval_seconds: Time between scans (default 2 minutes)
        """
        print(f"🔍 Starting hot machine monitor...")
        print(f"   Scan interval: {interval_seconds}s")
        print(f"   Press Ctrl+C to stop")
        print("")
        
        try:
            while True:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning for hot machines...")
                
                alerts = self.check_for_hot_machines()
                
                if alerts:
                    print(f"   🔥 Found {len(alerts)} hot machine(s)!")
                    for alert in alerts:
                        self.send_notification(alert)
                else:
                    print(f"   ✓ No hot machines detected")
                
                # Clear notified set every hour (allow re-alerts)
                if len(self.notified_machines) > 0:
                    self.notified_machines.clear()
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts from database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT machine_id, alert_time, hot_score, 
                       predicted_minutes, classification, alert_type
                FROM hot_machine_alerts
                WHERE alert_time > NOW() - INTERVAL '%s hours'
                ORDER BY alert_time DESC
                LIMIT 50
            """, (hours,))
            
            columns = ['machine_id', 'alert_time', 'hot_score', 
                      'predicted_minutes', 'classification', 'alert_type']
            
            alerts = []
            for row in cursor.fetchall():
                alert = dict(zip(columns, row))
                alerts.append(alert)
            
            return alerts
        finally:
            conn.close()


# Quick test
if __name__ == "__main__":
    print("🎰 Hot Machine Alert System")
    print("="*50)
    
    alert_system = HotMachineAlertSystem()
    
    # Create alerts table
    alert_system.create_alerts_table()
    
    # Run one scan
    print("\n📊 Running single scan...")
    alerts = alert_system.check_for_hot_machines()
    
    if alerts:
        print(f"\n🔥 Found {len(alerts)} hot machine(s):")
        for alert in alerts:
            alert_system.send_notification(alert)
    else:
        print("\n✓ No hot machines detected currently")
    
    # Ask to run continuous
    print("\nRun continuous monitoring? (y/n): ", end='')
    response = input().strip().lower()
    
    if response == 'y':
        alert_system.run_monitor(interval_seconds=120)
