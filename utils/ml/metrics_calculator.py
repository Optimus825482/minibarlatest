"""
Metrics Calculator - ML Anomaly Detection System
Metrik hesaplama servisi: Stok bitiş tahmini, trend analizi
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import numpy as np
from sklearn.linear_model import LinearRegression
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Metrik hesaplama servisi"""
    
    def __init__(self, db):
        self.db = db
    
    def predict_stock_depletion(self, urun_id):
        """
        Stok bitiş tarihini tahmin et (Linear Regression)
        Args:
            urun_id: Ürün ID
        Returns: (tahmini_gun, gunluk_tuketim, mevcut_stok)
        """
        try:
            from models import Urun, StokHareket, MLMetric
            
            urun = Urun.query.filter_by(id=urun_id).first()
            if not urun:
                return None, 0, 0
            
            # Son 30 günlük stok metriklerini al
            son_30_gun = datetime.now(timezone.utc) - timedelta(days=30)
            
            metrikler = MLMetric.query.filter(
                MLMetric.metric_type == 'stok_seviye',
                MLMetric.entity_id == urun_id,
                MLMetric.timestamp >= son_30_gun
            ).order_by(MLMetric.timestamp).all()
            
            if len(metrikler) < 7:
                # Yetersiz veri, basit hesaplama yap
                # Son 7 günlük çıkışları al
                son_7_gun = datetime.now(timezone.utc) - timedelta(days=7)
                cikis_toplam = self.db.session.query(
                    func.coalesce(func.sum(StokHareket.miktar), 0)
                ).filter(
                    StokHareket.urun_id == urun_id,
                    StokHareket.hareket_tipi == 'cikis',
                    StokHareket.islem_tarihi >= son_7_gun
                ).scalar()
                
                gunluk_tuketim = cikis_toplam / 7 if cikis_toplam > 0 else 0
                
                # Mevcut stok
                giris_toplam = self.db.session.query(
                    func.coalesce(func.sum(StokHareket.miktar), 0)
                ).filter(
                    StokHareket.urun_id == urun_id,
                    StokHareket.hareket_tipi == 'giris'
                ).scalar()
                
                cikis_toplam_all = self.db.session.query(
                    func.coalesce(func.sum(StokHareket.miktar), 0)
                ).filter(
                    StokHareket.urun_id == urun_id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar()
                
                mevcut_stok = giris_toplam - cikis_toplam_all
                
                if gunluk_tuketim > 0:
                    tahmini_gun = int(mevcut_stok / gunluk_tuketim)
                else:
                    tahmini_gun = 999  # Tüketim yok
                
                return tahmini_gun, gunluk_tuketim, mevcut_stok
            
            # Linear Regression ile tahmin
            X = np.array([(m.timestamp - metrikler[0].timestamp).days for m in metrikler]).reshape(-1, 1)
            y = np.array([m.metric_value for m in metrikler])
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Günlük tüketim (slope)
            gunluk_tuketim = abs(model.coef_[0])
            
            # Mevcut stok (son metrik)
            mevcut_stok = metrikler[-1].metric_value
            
            # Tahmini gün
            if gunluk_tuketim > 0:
                tahmini_gun = int(mevcut_stok / gunluk_tuketim)
            else:
                tahmini_gun = 999
            
            return tahmini_gun, gunluk_tuketim, mevcut_stok
            
        except Exception as e:
            logger.error(f"❌ Stok bitiş tahmini hatası: {str(e)}")
            return None, 0, 0
    
    def calculate_consumption_trend(self, oda_id, days=7):
        """
        Tüketim trendini hesapla
        Args:
            oda_id: Oda ID
            days: Kaç günlük trend
        Returns: (trend, ortalama, son_deger)
        """
        try:
            from models import MLMetric
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            metrikler = MLMetric.query.filter(
                MLMetric.metric_type == 'tuketim_miktar',
                MLMetric.entity_id == oda_id,
                MLMetric.timestamp >= cutoff_date
            ).order_by(MLMetric.timestamp).all()
            
            if len(metrikler) < 2:
                return 'stable', 0, 0
            
            values = [m.metric_value for m in metrikler]
            ortalama = np.mean(values)
            son_deger = values[-1]
            
            # Trend hesaplama (basit: ilk yarı vs son yarı)
            mid = len(values) // 2
            first_half_avg = np.mean(values[:mid])
            second_half_avg = np.mean(values[mid:])
            
            diff_percent = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
            
            if diff_percent > 20:
                trend = 'increasing'
            elif diff_percent < -20:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            return trend, ortalama, son_deger
            
        except Exception as e:
            logger.error(f"❌ Tüketim trend hesaplama hatası: {str(e)}")
            return 'stable', 0, 0
    
    def calculate_average_dolum_time(self, kat_sorumlusu_id):
        """
        Ortalama dolum süresini hesapla
        Args:
            kat_sorumlusu_id: Kat sorumlusu ID
        Returns: Ortalama dolum süresi (dakika)
        """
        try:
            from models import MLMetric
            
            # Son 30 günlük dolum metriklerini al
            son_30_gun = datetime.now(timezone.utc) - timedelta(days=30)
            
            metrikler = MLMetric.query.filter(
                MLMetric.metric_type == 'dolum_sure',
                MLMetric.entity_id == kat_sorumlusu_id,
                MLMetric.timestamp >= son_30_gun
            ).all()
            
            if not metrikler:
                return 0
            
            values = [m.metric_value for m in metrikler]
            ortalama = np.mean(values)
            
            return ortalama
            
        except Exception as e:
            logger.error(f"❌ Ortalama dolum süresi hesaplama hatası: {str(e)}")
            return 0
    
    def check_stock_depletion_alerts(self):
        """
        Tüm ürünler için stok bitiş kontrolü yap ve alert oluştur
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import Urun, MLAlert
            
            urunler = Urun.query.filter_by(aktif=True).all()
            
            alert_count = 0
            
            for urun in urunler:
                tahmini_gun, gunluk_tuketim, mevcut_stok = self.predict_stock_depletion(urun.id)
                
                if tahmini_gun is None:
                    continue
                
                # 7 gün veya daha az kaldıysa alert oluştur
                if tahmini_gun <= 7:
                    # Son 24 saatte aynı ürün için alert var mı kontrol et
                    son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
                    existing_alert = MLAlert.query.filter(
                        MLAlert.alert_type == 'stok_bitis_uyari',
                        MLAlert.entity_id == urun.id,
                        MLAlert.created_at >= son_24_saat,
                        MLAlert.is_false_positive == False
                    ).first()
                    
                    if not existing_alert:
                        # Severity belirle
                        if tahmini_gun <= 2:
                            severity = 'kritik'
                        elif tahmini_gun <= 4:
                            severity = 'yuksek'
                        else:
                            severity = 'orta'
                        
                        message = f"{urun.urun_adi} stoku {tahmini_gun} gün içinde tükenecek (Mevcut: {int(mevcut_stok)}, Günlük tüketim: {gunluk_tuketim:.1f})"
                        suggested_action = f"Acil sipariş verin. Kritik seviye: {urun.kritik_stok_seviyesi}"
                        
                        alert = MLAlert(
                            alert_type='stok_bitis_uyari',
                            severity=severity,
                            entity_type='urun',
                            entity_id=urun.id,
                            metric_value=mevcut_stok,
                            expected_value=gunluk_tuketim * 7,  # 7 günlük ideal stok
                            deviation_percent=0,
                            message=message,
                            suggested_action=suggested_action
                        )
                        self.db.session.add(alert)
                        alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} stok bitiş uyarısı oluşturuldu")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Stok bitiş kontrolü hatası: {str(e)}")
            return 0
    
    def get_dashboard_metrics(self):
        """
        Dashboard için özet metrikleri hesapla
        Returns: Metrik dict'i
        """
        try:
            from models import MLMetric, MLAlert, Urun
            
            # Son 24 saat metrikleri
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            
            stok_metrik_count = MLMetric.query.filter(
                MLMetric.metric_type == 'stok_seviye',
                MLMetric.timestamp >= son_24_saat
            ).count()
            
            tuketim_metrik_count = MLMetric.query.filter(
                MLMetric.metric_type == 'tuketim_miktar',
                MLMetric.timestamp >= son_24_saat
            ).count()
            
            # Aktif alertler
            aktif_alert_count = MLAlert.query.filter_by(
                is_read=False,
                is_false_positive=False
            ).count()
            
            # Kritik stok ürünleri
            kritik_urunler = []
            urunler = Urun.query.filter_by(aktif=True).all()
            
            for urun in urunler:
                tahmini_gun, _, mevcut_stok = self.predict_stock_depletion(urun.id)
                if tahmini_gun is not None and tahmini_gun <= 7:
                    kritik_urunler.append({
                        'urun': urun,
                        'tahmini_gun': tahmini_gun,
                        'mevcut_stok': int(mevcut_stok)
                    })
            
            return {
                'stok_metrik_count_24h': stok_metrik_count,
                'tuketim_metrik_count_24h': tuketim_metrik_count,
                'aktif_alert_count': aktif_alert_count,
                'kritik_urun_count': len(kritik_urunler),
                'kritik_urunler': kritik_urunler[:10]  # İlk 10 kritik ürün
            }
            
        except Exception as e:
            logger.error(f"❌ Dashboard metrik hesaplama hatası: {str(e)}")
            return {}
