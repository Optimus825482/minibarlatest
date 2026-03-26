"""
Negatif Stok Anomali Detektörü
Gerçek zamanlı negatif stok tespiti ve uyarı sistemi
"""
from models import db, Urun, StokHareket, MLAlert
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


class NegativeStockDetector:
    """Negatif stok anomali detektörü"""
    
    def __init__(self):
        pass
    
    def check_all_products(self):
        """Tüm ürünlerde negatif stok kontrolü yap"""
        try:
            logger.info("🔍 Negatif stok kontrolü başlatılıyor...")
            
            urunler = Urun.query.filter_by(aktif=True).all()
            negative_count = 0
            alerts_created = 0
            
            for urun in urunler:
                result = self.check_product_stock(urun.id)
                
                if result and result['is_negative']:
                    negative_count += 1
                    
                    # Alert oluştur
                    if self.create_alert(urun, result):
                        alerts_created += 1
            
            if negative_count > 0:
                logger.warning(f"⚠️  {negative_count} ürün negatif stokta! {alerts_created} alert oluşturuldu.")
            else:
                logger.info("✅ Negatif stok bulunamadı.")
            
            return {
                'total_checked': len(urunler),
                'negative_count': negative_count,
                'alerts_created': alerts_created
            }
            
        except Exception as e:
            logger.error(f"❌ Negatif stok kontrolü hatası: {str(e)}")
            return None
    
    def check_product_stock(self, urun_id):
        """Belirli bir ürünün stok durumunu kontrol et"""
        try:
            # Giriş ve çıkış toplamları
            giris = db.session.query(func.sum(StokHareket.miktar)).filter(
                StokHareket.urun_id == urun_id,
                StokHareket.hareket_tipi == 'giris'
            ).scalar() or 0
            
            cikis = db.session.query(func.sum(StokHareket.miktar)).filter(
                StokHareket.urun_id == urun_id,
                StokHareket.hareket_tipi == 'cikis'
            ).scalar() or 0
            
            mevcut_stok = giris - cikis
            
            return {
                'urun_id': urun_id,
                'giris': giris,
                'cikis': cikis,
                'mevcut_stok': mevcut_stok,
                'is_negative': mevcut_stok < 0,
                'fark': abs(mevcut_stok) if mevcut_stok < 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Ürün {urun_id} stok kontrolü hatası: {str(e)}")
            return None
    
    def create_alert(self, urun, stock_info):
        """Negatif stok için alert oluştur"""
        try:
            # Son 1 saatte aynı ürün için alert var mı kontrol et
            son_1_saat = datetime.now(timezone.utc) - timedelta(hours=1)
            
            existing_alert = MLAlert.query.filter(
                MLAlert.alert_type == "stok_anomali",
                MLAlert.entity_type == "urun",
                MLAlert.entity_id == urun.id,
                MLAlert.created_at >= son_1_saat,
                not MLAlert.is_false_positive,
            ).first()
            
            if existing_alert:
                logger.debug(f"Son 1 saatte {urun.urun_adi} için alert zaten var, atlanıyor.")
                return False
            
            # Yeni alert oluştur
            alert = MLAlert(
                alert_type='stok_anomali',
                severity='kritik',
                entity_type='urun',
                entity_id=urun.id,
                metric_value=stock_info['mevcut_stok'],
                expected_value=0,
                deviation_percent=100,
                message=f"🚨 NEGATİF STOK: {urun.urun_adi} - Mevcut: {stock_info['mevcut_stok']}, Giriş: {stock_info['giris']}, Çıkış: {stock_info['cikis']}",
                suggested_action=f"ACİL: {stock_info['fark']} adet giriş yapılmalı veya stok hareketleri kontrol edilmeli. Veri tutarsızlığı olabilir."
            )
            
            db.session.add(alert)
            db.session.commit()
            
            logger.warning(f"⚠️  Alert oluşturuldu: {urun.urun_adi} - Negatif stok: {stock_info['mevcut_stok']}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Alert oluşturma hatası: {str(e)}")
            return False
    
    def auto_fix_negative_stock(self, urun_id, islem_yapan_id=1):
        """Negatif stoku otomatik düzelt"""
        try:
            stock_info = self.check_product_stock(urun_id)
            
            if not stock_info or not stock_info['is_negative']:
                return False

            urun = db.session.get(Urun, urun_id)
            if not urun:
                return False
            
            # Düzeltme hareketi oluştur
            duzeltme_hareketi = StokHareket(
                urun_id=urun_id,
                hareket_tipi='giris',
                miktar=stock_info['fark'],
                aciklama=f"Otomatik Sistem Düzeltmesi - Negatif stok düzeltildi (Önceki: {stock_info['mevcut_stok']})",
                islem_yapan_id=islem_yapan_id,
                islem_tarihi=datetime.now(timezone.utc)
            )
            
            db.session.add(duzeltme_hareketi)
            db.session.commit()
            
            logger.info(f"✅ Otomatik düzeltme: {urun.urun_adi} - +{stock_info['fark']} giriş eklendi")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Otomatik düzeltme hatası: {str(e)}")
            return False


# Scheduled job için fonksiyon
def scheduled_negative_stock_check():
    """APScheduler için negatif stok kontrolü"""
    try:
        detector = NegativeStockDetector()
        result = detector.check_all_products()
        
        if result and result['negative_count'] > 0:
            logger.warning(f"⚠️  Scheduled check: {result['negative_count']} negatif stok tespit edildi!")
        
        return result
    except Exception as e:
        logger.error(f"❌ Scheduled negative stock check hatası: {str(e)}")
        return None
