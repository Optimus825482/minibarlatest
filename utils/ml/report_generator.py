"""
Report Generator - ML Anomaly Detection System
Rapor oluşturma servisi
"""

from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Rapor oluşturma servisi"""
    
    def __init__(self, db):
        self.db = db
    
    def generate_weekly_report(self):
        """Haftalık anomali raporu oluştur"""
        try:
            from utils.ml.alert_manager import AlertManager
            
            alert_manager = AlertManager(self.db)
            stats = alert_manager.get_alert_statistics(days=7)
            
            report = {
                'period': 'weekly',
                'start_date': (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
                'end_date': datetime.now(timezone.utc).isoformat(),
                'statistics': stats
            }
            
            logger.info("✅ Haftalık rapor oluşturuldu")
            return report
            
        except Exception as e:
            logger.error(f"❌ Haftalık rapor hatası: {str(e)}")
            return None
    
    def generate_monthly_report(self):
        """Aylık anomali raporu oluştur"""
        try:
            from utils.ml.alert_manager import AlertManager
            
            alert_manager = AlertManager(self.db)
            stats = alert_manager.get_alert_statistics(days=30)
            
            report = {
                'period': 'monthly',
                'start_date': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                'end_date': datetime.now(timezone.utc).isoformat(),
                'statistics': stats
            }
            
            logger.info("✅ Aylık rapor oluşturuldu")
            return report
            
        except Exception as e:
            logger.error(f"❌ Aylık rapor hatası: {str(e)}")
            return None
