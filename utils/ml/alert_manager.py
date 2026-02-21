"""
Alert Manager - ML Anomaly Detection System
Uyarı yönetim servisi: Alert oluşturma, okuma, yanlış pozitif işaretleme
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class AlertManager:
    """Uyarı yönetim servisi"""
    
    def __init__(self, db):
        self.db = db
    
    def create_alert(self, alert_data):
        """
        Yeni alert oluştur
        Args:
            alert_data: Alert bilgileri (dict)
        Returns: Alert ID veya None
        """
        try:
            from utils.ml_toggle import is_ml_enabled
            if not is_ml_enabled():
                logger.info("ML sistemi devre dışı - alert oluşturulmadı")
                return None
            
            from models import MLAlert
            
            alert = MLAlert(**alert_data)
            self.db.session.add(alert)
            self.db.session.commit()
            
            logger.info(f"✅ Alert oluşturuldu: {alert.alert_type} - {alert.severity}")
            
            return alert.id
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Alert oluşturma hatası: {str(e)}")
            return None
    
    def get_active_alerts(self, severity=None, limit=None):
        """
        Aktif alertleri getir
        Args:
            severity: Önem seviyesi filtresi (opsiyonel)
            limit: Maksimum kayıt sayısı (opsiyonel)
        Returns: Alert listesi
        """
        try:
            from models import MLAlert
            
            query = MLAlert.query.filter_by(is_read=False, is_false_positive=False)
            
            if severity:
                query = query.filter_by(severity=severity)
            
            query = query.order_by(
                MLAlert.severity.desc(),
                MLAlert.created_at.desc()
            )
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"❌ Alert getirme hatası: {str(e)}")
            return []
    
    def get_all_alerts(self, days=7, severity=None, alert_type=None):
        """
        Tüm alertleri getir (okunmuş dahil)
        Args:
            days: Son kaç günlük alertler
            severity: Önem seviyesi filtresi
            alert_type: Alert tipi filtresi
        Returns: Alert listesi
        """
        try:
            from models import MLAlert
            from datetime import timedelta
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = MLAlert.query.filter(
                MLAlert.created_at >= cutoff_date,
                MLAlert.is_false_positive == False
            )
            
            if severity:
                query = query.filter_by(severity=severity)
            
            if alert_type:
                query = query.filter_by(alert_type=alert_type)
            
            query = query.order_by(MLAlert.created_at.desc())
            
            return query.all()
            
        except Exception as e:
            logger.error(f"❌ Alert getirme hatası: {str(e)}")
            return []
    
    def mark_as_read(self, alert_id, user_id):
        """
        Alert'i okundu olarak işaretle
        Args:
            alert_id: Alert ID
            user_id: Okuyan kullanıcı ID
        Returns: Başarılı mı (bool)
        """
        try:
            from models import MLAlert
            
            alert = MLAlert.query.filter_by(id=alert_id).first()
            
            if not alert:
                logger.warning(f"Alert bulunamadı: {alert_id}")
                return False
            
            alert.is_read = True
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by_id = user_id
            
            self.db.session.commit()
            
            logger.info(f"✅ Alert okundu: {alert_id}")
            
            return True
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Alert okuma hatası: {str(e)}")
            return False
    
    def mark_as_false_positive(self, alert_id, user_id):
        """
        Yanlış pozitif olarak işaretle
        Args:
            alert_id: Alert ID
            user_id: İşaretleyen kullanıcı ID
        Returns: Başarılı mı (bool)
        """
        try:
            from models import MLAlert
            
            alert = MLAlert.query.filter_by(id=alert_id).first()
            
            if not alert:
                logger.warning(f"Alert bulunamadı: {alert_id}")
                return False
            
            alert.is_false_positive = True
            alert.is_read = True
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by_id = user_id
            
            self.db.session.commit()
            
            logger.info(f"⚠️  Alert yanlış pozitif: {alert_id}")
            
            return True
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Yanlış pozitif işaretleme hatası: {str(e)}")
            return False
    
    def get_alert_statistics(self, days=30):
        """
        Alert istatistiklerini getir
        Args:
            days: Son kaç günlük istatistikler
        Returns: İstatistik dict'i
        """
        try:
            from models import MLAlert
            from datetime import timedelta
            from sqlalchemy import func
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Toplam alert sayısı
            total_alerts = MLAlert.query.filter(
                MLAlert.created_at >= cutoff_date
            ).count()
            
            # Okunmamış alert sayısı
            unread_alerts = MLAlert.query.filter(
                MLAlert.created_at >= cutoff_date,
                MLAlert.is_read == False,
                MLAlert.is_false_positive == False
            ).count()
            
            # Yanlış pozitif sayısı
            false_positives = MLAlert.query.filter(
                MLAlert.created_at >= cutoff_date,
                MLAlert.is_false_positive == True
            ).count()
            
            # Severity dağılımı
            severity_dist = self.db.session.query(
                MLAlert.severity,
                func.count(MLAlert.id)
            ).filter(
                MLAlert.created_at >= cutoff_date,
                MLAlert.is_false_positive == False
            ).group_by(MLAlert.severity).all()
            
            # Alert tipi dağılımı
            type_dist = self.db.session.query(
                MLAlert.alert_type,
                func.count(MLAlert.id)
            ).filter(
                MLAlert.created_at >= cutoff_date,
                MLAlert.is_false_positive == False
            ).group_by(MLAlert.alert_type).all()
            
            return {
                'total_alerts': total_alerts,
                'unread_alerts': unread_alerts,
                'false_positives': false_positives,
                'false_positive_rate': (false_positives / total_alerts * 100) if total_alerts > 0 else 0,
                'severity_distribution': {s: c for s, c in severity_dist},
                'type_distribution': {t: c for t, c in type_dist}
            }
            
        except Exception as e:
            logger.error(f"❌ İstatistik hesaplama hatası: {str(e)}")
            return {}
    
    def send_notification(self, alert):
        """
        ML Alert için email bildirimi gönder
        Args:
            alert: MLAlert objesi
        Returns: Başarılı mı (bool)
        """
        try:
            from utils.ml_toggle import is_ml_enabled
            if not is_ml_enabled():
                logger.info("ML sistemi devre dışı - email bildirimi gönderilmedi")
                return False
            
            from utils.email_service import EmailService
            from models import Kullanici
            
            # Severity'ye göre alıcıları belirle
            if alert.severity in ['kritik', 'yuksek']:
                # Kritik ve yüksek alertler için sistem yöneticileri + depo sorumluları
                alicilar = Kullanici.query.filter(
                    Kullanici.rol.in_(['sistem_yoneticisi', 'admin', 'depo_sorumlusu']),
                    Kullanici.aktif == True,
                    Kullanici.email.isnot(None)
                ).all()
            else:
                # Düşük ve orta alertler için sadece sistem yöneticileri
                alicilar = Kullanici.query.filter(
                    Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                    Kullanici.aktif == True,
                    Kullanici.email.isnot(None)
                ).all()
            
            if not alicilar:
                logger.warning("ML Alert bildirimi için alıcı bulunamadı")
                return False
            
            # Severity'ye göre emoji ve renk
            severity_config = {
                'kritik': {'emoji': '🚨', 'color': '#dc2626', 'label': 'KRİTİK'},
                'yuksek': {'emoji': '⚠️', 'color': '#ea580c', 'label': 'YÜKSEK'},
                'orta': {'emoji': '📊', 'color': '#ca8a04', 'label': 'ORTA'},
                'dusuk': {'emoji': 'ℹ️', 'color': '#2563eb', 'label': 'DÜŞÜK'}
            }
            config = severity_config.get(alert.severity, severity_config['orta'])
            
            # Alert tipi açıklaması
            alert_type_labels = {
                'stok_anomali': 'Stok Anomalisi',
                'tuketim_anomali': 'Tüketim Anomalisi',
                'dolum_gecikme': 'Dolum Gecikmesi',
                'stok_bitis_uyari': 'Stok Bitiş Uyarısı',
                'zimmet_fire_yuksek': 'Yüksek Zimmet Fire',
                'bosta_tuketim_var': 'Boş Oda Tüketimi',
                'doluda_tuketim_yok': 'Dolu Oda Tüketim Yok',
                'talep_yanitlanmadi': 'Yanıtlanmayan Talep',
                'talep_yogunluk_yuksek': 'Yüksek Talep Yoğunluğu',
                'qr_kullanim_dusuk': 'Düşük QR Kullanımı'
            }
            alert_type_label = alert_type_labels.get(alert.alert_type, alert.alert_type)
            
            subject = f"{config['emoji']} ML Alert [{config['label']}]: {alert_type_label}"
            
            body = f"""ML Anomali Tespit Sistemi Uyarısı

Seviye: {config['label']}
Tip: {alert_type_label}
Tarih: {alert.created_at.strftime('%d.%m.%Y %H:%M')}

Mesaj:
{alert.message}

Önerilen Aksiyon:
{alert.suggested_action or 'Belirtilmemiş'}

Metrik Değeri: {alert.metric_value:.2f}
Beklenen Değer: {f'{alert.expected_value:.2f}' if alert.expected_value else 'N/A'}
Sapma Oranı: %{abs(alert.deviation_percent):.1f if alert.deviation_percent else 0}

---
Minibar Takip ML Sistemi
"""
            
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
    <div style="background: {config['color']}; padding: 20px; border-radius: 10px 10px 0 0;">
        <h2 style="color: white; margin: 0;">{config['emoji']} ML Alert - {config['label']}</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0;">{alert_type_label}</p>
    </div>
    <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
        <div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin: 0; font-size: 16px;"><strong>{alert.message}</strong></p>
        </div>
        
        <div style="background: #fef3c7; border-left: 4px solid {config['color']}; padding: 15px; margin: 15px 0;">
            <strong>📋 Önerilen Aksiyon:</strong>
            <p style="margin: 10px 0 0 0;">{alert.suggested_action or 'Belirtilmemiş'}</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Metrik Değeri:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{alert.metric_value:.2f}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Beklenen Değer:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{f'{alert.expected_value:.2f}' if alert.expected_value else 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Sapma Oranı:</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">%{abs(alert.deviation_percent):.1f if alert.deviation_percent else 0}</td>
            </tr>
            <tr>
                <td style="padding: 8px;"><strong>Tarih:</strong></td>
                <td style="padding: 8px;">{alert.created_at.strftime('%d.%m.%Y %H:%M')}</td>
            </tr>
        </table>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
        <p style="color: #9ca3af; font-size: 12px; margin: 0;">Minibar Takip ML Anomali Tespit Sistemi</p>
    </div>
</body>
</html>
"""
            
            gonderilen = 0
            for alici in alicilar:
                result = EmailService.send_email(
                    to_email=alici.email,
                    subject=subject,
                    body=body,
                    email_tipi='uyari',
                    kullanici_id=alici.id,
                    ilgili_tablo='ml_alerts',
                    ilgili_kayit_id=alert.id,
                    html_body=html_body,
                    ek_bilgiler={
                        'alert_type': alert.alert_type,
                        'severity': alert.severity,
                        'entity_id': alert.entity_id
                    }
                )
                if result['success']:
                    gonderilen += 1
            
            logger.info(f"📧 ML Alert bildirimi gönderildi: {gonderilen}/{len(alicilar)} alıcı")
            return gonderilen > 0
            
        except Exception as e:
            logger.error(f"❌ ML Alert bildirim hatası: {str(e)}")
            return False
    
    def send_critical_alerts_summary(self):
        """
        Kritik alertlerin özetini gönder (günlük)
        Returns: Gönderilen email sayısı
        """
        try:
            from utils.ml_toggle import is_ml_enabled
            if not is_ml_enabled():
                logger.info("ML sistemi devre dışı - kritik alert özeti gönderilmedi")
                return 0
            
            from utils.email_service import EmailService
            from models import Kullanici, MLAlert
            from datetime import timedelta
            
            # Son 24 saatteki kritik ve yüksek alertleri al
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            
            kritik_alertler = MLAlert.query.filter(
                MLAlert.created_at >= son_24_saat,
                MLAlert.severity.in_(['kritik', 'yuksek']),
                MLAlert.is_false_positive == False
            ).order_by(MLAlert.severity.desc(), MLAlert.created_at.desc()).all()
            
            if not kritik_alertler:
                logger.info("Son 24 saatte kritik alert yok")
                return 0
            
            # Sistem yöneticilerini al
            alicilar = Kullanici.query.filter(
                Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            if not alicilar:
                return 0
            
            subject = f"📊 ML Günlük Alert Özeti - {len(kritik_alertler)} Kritik/Yüksek Alert"
            
            # Alert listesi oluştur
            alert_rows = ""
            for alert in kritik_alertler[:20]:  # Max 20 alert
                severity_emoji = '🚨' if alert.severity == 'kritik' else '⚠️'
                alert_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{severity_emoji} {alert.severity.upper()}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{alert.alert_type}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{alert.message[:50]}...</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{alert.created_at.strftime('%H:%M')}</td>
                </tr>
                """
            
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 700px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed, #4f46e5); padding: 20px; border-radius: 10px 10px 0 0;">
            <h2 style="color: white; margin: 0;">📊 ML Günlük Alert Özeti</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0;">Son 24 saat - {len(kritik_alertler)} kritik/yüksek alert</p>
        </div>
        <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f9fafb;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Seviye</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Tip</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Mesaj</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Saat</th>
                    </tr>
                </thead>
                <tbody>
                    {alert_rows}
                </tbody>
            </table>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
            <p style="color: #9ca3af; font-size: 12px;">Minibar Takip ML Sistemi</p>
        </div>
    </div>
</body>
</html>
"""
            
            gonderilen = 0
            for alici in alicilar:
                result = EmailService.send_email(
                    to_email=alici.email,
                    subject=subject,
                    body=f"Son 24 saatte {len(kritik_alertler)} kritik/yüksek ML alert tespit edildi.",
                    email_tipi='bilgi',
                    kullanici_id=alici.id,
                    ilgili_tablo='ml_alerts',
                    html_body=html_body
                )
                if result['success']:
                    gonderilen += 1
            
            logger.info(f"📧 ML Alert özeti gönderildi: {gonderilen} alıcı")
            return gonderilen
            
        except Exception as e:
            logger.error(f"❌ ML Alert özeti gönderim hatası: {str(e)}")
            return 0
    
    def cleanup_old_alerts(self, days=90):
        """
        Eski alertleri temizle
        Args:
            days: Kaç günden eski alertler silinecek
        Returns: Silinen kayıt sayısı
        """
        try:
            from models import MLAlert
            from datetime import timedelta
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            deleted_count = MLAlert.query.filter(
                MLAlert.created_at < cutoff_date,
                MLAlert.is_read == True
            ).delete()
            
            self.db.session.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️  {deleted_count} eski alert silindi ({days} günden eski)")
            
            return deleted_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Alert temizleme hatası: {str(e)}")
            return 0
