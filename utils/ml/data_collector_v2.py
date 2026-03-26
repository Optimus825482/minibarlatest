"""
Data Collector V2 - Optimized ML Data Collection System
- Duplicate önleme
- Incremental collection (sadece yeni veriler)
- Timestamp tracking
- Efficient queries
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


class DataCollectorV2:
    """Optimize edilmiş veri toplama servisi"""
    
    def __init__(self, db):
        self.db = db
        self.collection_interval = timedelta(minutes=15)  # Toplama aralığı
    
    def _get_last_collection_time(self, metric_type, entity_id=None):
        """Son veri toplama zamanını getir"""
        try:
            from models import MLMetric
            
            query = MLMetric.query.filter_by(metric_type=metric_type)
            
            if entity_id is not None:
                query = query.filter_by(entity_id=entity_id)
            
            last_metric = query.order_by(MLMetric.timestamp.desc()).first()
            
            if last_metric:
                return last_metric.timestamp
            return None
            
        except Exception as e:
            logger.error(f"Son toplama zamanı alınamadı: {str(e)}")
            return None
    
    def _should_collect(self, metric_type, entity_id=None):
        """Veri toplanmalı mı kontrol et"""
        last_time = self._get_last_collection_time(metric_type, entity_id)
        
        if last_time is None:
            return True  # İlk toplama
        
        # Son toplamadan beri yeterli zaman geçti mi?
        time_since_last = datetime.now(timezone.utc) - last_time
        return time_since_last >= self.collection_interval
    
    def _check_duplicate(self, metric_type, entity_id, timestamp, tolerance_minutes=5):
        """
        Duplicate kontrol et
        Args:
            tolerance_minutes: Kaç dakika içindeki kayıtlar duplicate sayılır
        """
        try:
            from models import MLMetric
            
            # Tolerance aralığı
            start_time = timestamp - timedelta(minutes=tolerance_minutes)
            end_time = timestamp + timedelta(minutes=tolerance_minutes)
            
            existing = MLMetric.query.filter(
                MLMetric.metric_type == metric_type,
                MLMetric.entity_id == entity_id,
                MLMetric.timestamp.between(start_time, end_time)
            ).first()
            
            return existing is not None
            
        except Exception as e:
            logger.error(f"Duplicate kontrol hatası: {str(e)}")
            return False
    
    def collect_stok_metrics_incremental(self):
        """
        Stok metriklerini incremental topla
        Sadece değişen stokları kaydet
        """
        try:
            from models import Urun, StokHareket, MLMetric
            
            # Aktif ürünleri al
            urunler = Urun.query.filter_by(aktif=True).all()
            
            collected_count = 0
            skipped_count = 0
            timestamp = datetime.now(timezone.utc)
            
            for urun in urunler:
                # Duplicate kontrol
                if self._check_duplicate('stok_seviye', urun.id, timestamp):
                    skipped_count += 1
                    continue
                
                # Stok seviyesini hesapla
                giris_toplam = self.db.session.query(
                    func.coalesce(func.sum(StokHareket.miktar), 0)
                ).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'giris'
                ).scalar()
                
                cikis_toplam = self.db.session.query(
                    func.coalesce(func.sum(StokHareket.miktar), 0)
                ).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar()
                
                mevcut_stok = giris_toplam - cikis_toplam
                
                # Son kaydedilen stok değerini al
                last_metric = MLMetric.query.filter_by(
                    metric_type='stok_seviye',
                    entity_id=urun.id
                ).order_by(MLMetric.timestamp.desc()).first()
                
                # Stok değişmişse kaydet
                if last_metric is None or abs(last_metric.metric_value - mevcut_stok) > 0.01:
                    metric = MLMetric(
                        metric_type='stok_seviye',
                        entity_id=urun.id,
                        metric_value=float(mevcut_stok),
                        timestamp=timestamp,
                        extra_data={
                            'urun_adi': urun.urun_adi,
                            'kritik_seviye': urun.kritik_stok_seviyesi,
                            'grup': urun.grup.grup_adi if urun.grup else None,
                            'degisim': float(mevcut_stok - (last_metric.metric_value if last_metric else 0))
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
                else:
                    skipped_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Stok metrikleri: {collected_count} yeni, {skipped_count} atlandı")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Stok metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_new_transactions_only(self):
        """
        Sadece yeni işlemleri topla (son toplama sonrası)
        """
        try:
            from models import StokHareket, MinibarIslem, MLMetric
            
            # Son veri toplama zamanı
            last_collection = self._get_last_collection_time('transaction_processed')
            
            if last_collection is None:
                # İlk toplama - son 24 saat
                last_collection = datetime.now(timezone.utc) - timedelta(hours=24)
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            # Yeni stok hareketleri
            new_stok_hareketleri = StokHareket.query.filter(
                StokHareket.islem_tarihi > last_collection
            ).all()
            
            for hareket in new_stok_hareketleri:
                # İşlem metriği kaydet
                metric = MLMetric(
                    metric_type='stok_hareket',
                    entity_id=hareket.urun_id,
                    metric_value=float(hareket.miktar if hareket.hareket_tipi == 'giris' else -hareket.miktar),
                    timestamp=hareket.islem_tarihi,
                    extra_data={
                        'hareket_tipi': hareket.hareket_tipi,
                        'hareket_id': hareket.id,
                        'aciklama': hareket.aciklama
                    }
                )
                self.db.session.add(metric)
                collected_count += 1
            
            # Yeni minibar işlemleri
            new_minibar_islemleri = MinibarIslem.query.filter(
                MinibarIslem.islem_tarihi > last_collection
            ).all()
            
            for islem in new_minibar_islemleri:
                # Tüketim metriği
                toplam_tuketim = sum(detay.tuketim for detay in islem.detaylar)
                
                if toplam_tuketim > 0:
                    metric = MLMetric(
                        metric_type='minibar_tuketim',
                        entity_id=islem.oda_id,
                        metric_value=float(toplam_tuketim),
                        timestamp=islem.islem_tarihi,
                        extra_data={
                            'islem_tipi': islem.islem_tipi,
                            'islem_id': islem.id,
                            'personel_id': islem.personel_id
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
            
            # İşlem tamamlandı işareti
            marker = MLMetric(
                metric_type='transaction_processed',
                entity_id=0,
                metric_value=float(collected_count),
                timestamp=timestamp,
                extra_data={
                    'last_collection': last_collection.isoformat(),
                    'new_transactions': collected_count
                }
            )
            self.db.session.add(marker)
            
            self.db.session.commit()
            logger.info(f"✅ Yeni işlemler toplandı: {collected_count} kayıt")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Yeni işlem toplama hatası: {str(e)}")
            return 0
    
    def collect_all_metrics_smart(self):
        """
        Tüm metrikleri akıllı topla
        - Duplicate önleme
        - Incremental collection
        - Sadece değişen veriler
        """
        try:
            logger.info("🔄 Akıllı veri toplama başladı...")
            
            # 1. Incremental stok metrikleri
            stok_count = self.collect_stok_metrics_incremental()
            
            # 2. Sadece yeni işlemler
            transaction_count = self.collect_new_transactions_only()
            
            # 3. Diğer metrikler (eski collector'dan)
            from utils.ml.data_collector import DataCollector
            old_collector = DataCollector(self.db)
            
            tuketim_count = old_collector.collect_tuketim_metrics()
            dolum_count = old_collector.collect_dolum_metrics()
            
            total_count = stok_count + transaction_count + tuketim_count + dolum_count
            
            logger.info(f"✅ Toplam {total_count} yeni metrik toplandı")
            logger.info(f"   - Stok (değişen): {stok_count}")
            logger.info(f"   - Yeni işlemler: {transaction_count}")
            logger.info(f"   - Tüketim: {tuketim_count}")
            logger.info(f"   - Dolum: {dolum_count}")
            
            return total_count
            
        except Exception as e:
            logger.error(f"❌ Akıllı veri toplama hatası: {str(e)}")
            return 0
    
    def get_collection_stats(self):
        """Veri toplama istatistikleri"""
        try:
            from models import MLMetric
            
            # Toplam metrik sayısı
            total_metrics = MLMetric.query.count()
            
            # Metrik tiplerine göre dağılım
            metric_distribution = self.db.session.query(
                MLMetric.metric_type,
                func.count(MLMetric.id).label('count')
            ).group_by(MLMetric.metric_type).all()
            
            # Son 24 saat
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_metrics = MLMetric.query.filter(
                MLMetric.timestamp >= son_24_saat
            ).count()
            
            # En eski ve en yeni metrik
            oldest = MLMetric.query.order_by(MLMetric.timestamp.asc()).first()
            newest = MLMetric.query.order_by(MLMetric.timestamp.desc()).first()
            
            stats = {
                'total_metrics': total_metrics,
                'recent_24h': recent_metrics,
                'distribution': {mt: count for mt, count in metric_distribution},
                'oldest_metric': oldest.timestamp.isoformat() if oldest else None,
                'newest_metric': newest.timestamp.isoformat() if newest else None,
                'data_range_days': (newest.timestamp - oldest.timestamp).days if oldest and newest else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"İstatistik hatası: {str(e)}")
            return {}


# Scheduled job için fonksiyon
def scheduled_smart_collection():
    """APScheduler için akıllı veri toplama"""
    try:
        from models import db
        collector = DataCollectorV2(db)
        result = collector.collect_all_metrics_smart()
        
        logger.info(f"✅ Scheduled smart collection: {result} metrik toplandı")
        return result
    except Exception as e:
        logger.error(f"❌ Scheduled smart collection hatası: {str(e)}")
        return 0
