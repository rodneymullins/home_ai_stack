#!/usr/bin/env python3
"""
Fellowship Alerts - Notification system for Fellowship events
Supports email, desktop notifications, and logging.
"""

import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FellowshipAlerts:
    """Alert system for Fellowship infrastructure."""
    
    def __init__(self, email_config=None):
        self.email_config = email_config or {}
        self.alert_log = []
    
    def desktop_notify(self, title, message):
        """Send macOS desktop notification."""
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', script], check=True)
            logger.info(f"💬 Desktop notification sent: {title}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Desktop notification failed: {e}")
            return False
    
    def email_notify(self, subject, body, to_email=None):
        """Send email notification (if configured)."""
        if not self.email_config.get('enabled'):
            logger.info("📧 Email not configured, skipping")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config.get('from_email')
            msg['To'] = to_email or self.email_config.get('to_email')
            msg['Subject'] = f"[Fellowship] {subject}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.email_config.get('smtp_server', 'localhost'),
                self.email_config.get('smtp_port', 587)
            )
            server.starttls()
            if self.email_config.get('smtp_user'):
                server.login(
                    self.email_config['smtp_user'],
                    self.email_config['smtp_password']
                )
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"📧 Email sent: {subject}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Email send failed: {e}")
            return False
    
    def log_alert(self, level, title, message):
        """Log alert to internal log."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'title': title,
            'message': message
        }
        self.alert_log.append(alert)
        logger.log(
            logging.WARNING if level == 'warning' else logging.ERROR if level == 'error' else logging.INFO,
            f"{title}: {message}"
        )
    
    def alert_endpoint_down(self, endpoint, duration_minutes=0):
        """Alert when endpoint is down."""
        title = f"⚠️ {endpoint} DOWN"
        message = f"{endpoint} has been unreachable"
        if duration_minutes > 0:
            message += f" for {duration_minutes} minutes"
        
        self.log_alert('error', title, message)
        self.desktop_notify(title, message)
        
        if duration_minutes >= 5:
            self.email_notify(title, message)
    
    def alert_failover(self, from_endpoint, to_endpoint, model):
        """Alert on failover event."""
        title = "🔄 Failover Occurred"
        message = f"Failed over from {from_endpoint} to {to_endpoint} for model {model}"
        
        self.log_alert('warning', title, message)
        self.desktop_notify(title, message)
    
    def alert_high_error_rate(self, endpoint, error_rate_pct):
        """Alert when error rate is high."""
        title = f"⚠️ High Error Rate on {endpoint}"
        message = f"Error rate: {error_rate_pct:.1f}%"
        
        self.log_alert('warning', title, message)
        self.desktop_notify(title, message)
        
        if error_rate_pct > 50:
            self.email_notify(title, message)
    
    def test_notifications(self):
        """Test all notification channels."""
        print("🧪 Testing notification channels...")
        
        # Desktop
        if self.desktop_notify("Test Alert", "This is a test from Fellowship"):
            print("✅ Desktop notifications working")
        else:
            print("❌ Desktop notifications failed")
        
        # Email
        if self.email_config.get('enabled'):
            if self.email_notify("Test Email", "This is a test email from Fellowship"):
                print("✅ Email notifications working")
            else:
                print("❌ Email notifications failed")
        else:
            print("⚠️  Email notifications not configured")


def main():
    """Test alerts."""
    alerts = FellowshipAlerts()
    
    # Test desktop notification
    alerts.desktop_notify(
        "🏰 Fellowship Alert",
        "Alert system initialized successfully"
    )
    
    # Simulate some alerts
    alerts.alert_failover("Aragorn", "Gandalf", "llama3.1:8b")
    
    print("\n📋 Alert Log:")
    for alert in alerts.alert_log:
        print(f"  [{alert['level']}] {alert['title']}: {alert['message']}")


if __name__ == '__main__':
    main()
