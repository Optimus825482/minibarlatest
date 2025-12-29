"""
Data Collector - ML Anomaly Detection System
Veri toplama servisi: Stok, tüketim ve dolum metriklerini toplar
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


class DataCollector:
    """Veri toplama servisi"""
    
    def __init__(self, db):
        self.db = db
    
    def collect_stok_metrics(self):
        """
        Tüm ürünler için stok seviyelerini topla
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import Urun, StokHareket, MLMetric
            
            # Aktif ürünleri al
            urunler = Urun.query.filter_by(aktif=True).all()
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            for urun in urunler:
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
                
                # Metrik kaydı oluştur
                metric = MLMetric(
                    metric_type='stok_seviye',
                    entity_id=urun.id,
                    metric_value=float(mevcut_stok),
                    timestamp=timestamp,
                    extra_data={
                        'urun_adi': urun.urun_adi,
                        'kritik_seviye': urun.kritik_stok_seviyesi,
                        'grup': urun.grup.grup_adi if urun.grup else None
                    }
                )
                self.db.session.add(metric)
                collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Stok metrikleri toplandı: {collected_count} ürün")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Stok metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_tuketim_metrics(self):
        """
        Oda bazlı tüketim verilerini topla (son 24 saat)
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import Oda, MinibarIslem, MinibarIslemDetay, MLMetric
            
            # Son 24 saatlik verileri al
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Aktif odaları al
            odalar = Oda.query.filter_by(aktif=True).all()
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            for oda in odalar:
                # Son 24 saatteki tüketimi hesapla
                tuketim_toplam = self.db.session.query(
                    func.coalesce(func.sum(MinibarIslemDetay.tuketim), 0)
                ).join(
                    MinibarIslem
                ).filter(
                    MinibarIslem.oda_id == oda.id,
                    MinibarIslem.islem_tarihi >= son_24_saat,
                    MinibarIslem.islem_tipi.in_(['ilk_dolum', 'yeniden_dolum', 'eksik_tamamlama', 'sayim'])
                ).scalar()
                
                # Sadece tüketim varsa kaydet
                if tuketim_toplam > 0:
                    metric = MLMetric(
                        metric_type='tuketim_oran',  # Railway'de: tuketim_oran
                        entity_id=oda.id,
                        metric_value=float(tuketim_toplam),
                        timestamp=timestamp,
                        extra_data={
                            'oda_no': oda.oda_no,
                            'oda_tipi': oda.oda_tipi_adi,
                            'kat': oda.kat.kat_adi if oda.kat else None
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Tüketim metrikleri toplandı: {collected_count} oda")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Tüketim metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_dolum_metrics(self):
        """
        Dolum süresi metriklerini topla (son 7 gün)
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import Kullanici, MinibarIslem, MLMetric
            
            # Son 7 günlük verileri al
            son_7_gun = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Kat sorumluları
            kat_sorumlulari = Kullanici.query.filter_by(
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            for personel in kat_sorumlulari:
                # Son 7 gündeki dolum işlemlerini al
                dolum_islemleri = MinibarIslem.query.filter(
                    MinibarIslem.personel_id == personel.id,
                    MinibarIslem.islem_tarihi >= son_7_gun,
                    MinibarIslem.islem_tipi.in_(['ilk_dolum', 'yeniden_dolum', 'eksik_tamamlama'])
                ).order_by(MinibarIslem.islem_tarihi).all()
                
                if len(dolum_islemleri) >= 2:
                    # Ortalama dolum süresini hesapla (işlemler arası süre)
                    sureler = []
                    for i in range(1, len(dolum_islemleri)):
                        onceki = dolum_islemleri[i-1].islem_tarihi
                        sonraki = dolum_islemleri[i].islem_tarihi
                        sure_dakika = (sonraki - onceki).total_seconds() / 60
                        sureler.append(sure_dakika)
                    
                    if sureler:
                        ortalama_sure = sum(sureler) / len(sureler)
                        
                        metric = MLMetric(
                            metric_type='dolum_sure',
                            entity_id=personel.id,
                            metric_value=float(ortalama_sure),
                            timestamp=timestamp,
                            extra_data={
                                'personel_adi': f"{personel.ad} {personel.soyad}",
                                'islem_sayisi': len(dolum_islemleri),
                                'otel': personel.otel.ad if personel.otel else None
                            }
                        )
                        self.db.session.add(metric)
                        collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Dolum süresi metrikleri toplandı: {collected_count} personel")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Dolum süresi metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_zimmet_metrics(self):
        """
        Zimmet kullanım ve fire metriklerini topla
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import Kullanici, PersonelZimmet, PersonelZimmetDetay, MLMetric
            
            # Aktif kat sorumluları
            kat_sorumlulari = Kullanici.query.filter_by(
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            for personel in kat_sorumlulari:
                # Aktif zimmetleri al
                aktif_zimmetler = PersonelZimmet.query.filter_by(
                    personel_id=personel.id,
                    durum='aktif'
                ).all()
                
                if not aktif_zimmetler:
                    continue
                
                toplam_zimmet = 0
                toplam_kullanim = 0
                toplam_fire = 0
                
                for zimmet in aktif_zimmetler:
                    for detay in zimmet.detaylar:
                        toplam_zimmet += detay.miktar
                        toplam_kullanim += detay.kullanilan_miktar
                        # Fire = Zimmet - Kullanılan - Kalan
                        fire = detay.miktar - detay.kullanilan_miktar - (detay.kalan_miktar or 0)
                        toplam_fire += max(0, fire)
                
                if toplam_zimmet > 0:
                    # Kullanım oranı
                    kullanim_oran = (toplam_kullanim / toplam_zimmet * 100)
                    metric = MLMetric(
                        metric_type='zimmet_kullanim',
                        entity_id=personel.id,
                        metric_value=float(kullanim_oran),
                        timestamp=timestamp,
                        extra_data={
                            'personel_adi': f"{personel.ad} {personel.soyad}",
                            'toplam_zimmet': toplam_zimmet,
                            'toplam_kullanim': toplam_kullanim
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
                    
                    # Fire oranı
                    fire_oran = (toplam_fire / toplam_zimmet * 100)
                    metric = MLMetric(
                        metric_type='zimmet_fire',
                        entity_id=personel.id,
                        metric_value=float(fire_oran),
                        timestamp=timestamp,
                        extra_data={
                            'personel_adi': f"{personel.ad} {personel.soyad}",
                            'toplam_zimmet': toplam_zimmet,
                            'toplam_fire': toplam_fire
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Zimmet metrikleri toplandı: {collected_count} kayıt")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Zimmet metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_occupancy_metrics(self):
        """
        Doluluk ve boş oda tüketim metriklerini topla
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import Oda, MisafirKayit, MinibarIslem, MinibarIslemDetay, MLMetric
            
            # Son 24 saat
            simdi = datetime.now(timezone.utc)
            son_24_saat = simdi - timedelta(hours=24)
            
            # Aktif odaları al
            odalar = Oda.query.filter_by(aktif=True).all()
            
            collected_count = 0
            timestamp = simdi
            
            for oda in odalar:
                # Oda dolu mu kontrol et (son 24 saatte arrival var mı?)
                misafir = MisafirKayit.query.filter(
                    MisafirKayit.oda_id == oda.id,
                    MisafirKayit.kayit_tipi == 'arrival',
                    MisafirKayit.giris_tarihi >= son_24_saat.date()
                ).order_by(MisafirKayit.giris_tarihi.desc()).first()
                
                # In-house kayıtları kontrol et (hala odada mı?)
                in_house = MisafirKayit.query.filter(
                    MisafirKayit.oda_id == oda.id,
                    MisafirKayit.kayit_tipi == 'in_house',
                    MisafirKayit.giris_tarihi <= simdi.date(),
                    MisafirKayit.cikis_tarihi >= simdi.date()
                ).order_by(MisafirKayit.giris_tarihi.desc()).first()
                
                # Oda durumu belirle
                oda_dolu = False
                if in_house:
                    oda_dolu = True
                elif misafir and misafir.cikis_tarihi >= simdi.date():
                    oda_dolu = True
                
                # Son 24 saatteki tüketimi hesapla
                tuketim_toplam = self.db.session.query(
                    func.coalesce(func.sum(MinibarIslemDetay.tuketim), 0)
                ).join(
                    MinibarIslem
                ).filter(
                    MinibarIslem.oda_id == oda.id,
                    MinibarIslem.islem_tarihi >= son_24_saat
                ).scalar()
                
                # Boş oda ama tüketim var mı?
                if not oda_dolu and tuketim_toplam > 0:
                    metric = MLMetric(
                        metric_type='bosta_tuketim',
                        entity_id=oda.id,
                        metric_value=float(tuketim_toplam),
                        timestamp=timestamp,
                        extra_data={
                            'oda_no': oda.oda_no,
                            'oda_dolu': False,
                            'tuketim': int(tuketim_toplam)
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Doluluk metrikleri toplandı: {collected_count} kayıt")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Doluluk metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_talep_metrics(self):
        """
        Misafir dolum talep metriklerini topla
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import MinibarDolumTalebi, Oda, MLMetric
            
            # Son 24 saatlik talepler
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            
            talepler = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.talep_tarihi >= son_24_saat
            ).all()
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            # Oda bazlı talep yoğunluğu
            oda_talep_sayilari = {}
            
            for talep in talepler:
                # Talep yanıt süresi (tamamlanan talepler için)
                if talep.durum == 'tamamlandi' and talep.tamamlanma_tarihi:
                    yanit_sure = (talep.tamamlanma_tarihi - talep.talep_tarihi).total_seconds() / 60  # dakika
                    
                    metric = MLMetric(
                        metric_type='talep_yanit_sure',
                        entity_id=talep.oda_id,
                        metric_value=float(yanit_sure),
                        timestamp=timestamp,
                        extra_data={
                            'oda_no': talep.oda.oda_no if talep.oda else None,
                            'talep_id': talep.id
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
                
                # Talep yoğunluğu sayımı
                if talep.oda_id not in oda_talep_sayilari:
                    oda_talep_sayilari[talep.oda_id] = 0
                oda_talep_sayilari[talep.oda_id] += 1
            
            # Talep yoğunluğu metriklerini kaydet
            for oda_id, talep_sayisi in oda_talep_sayilari.items():
                oda = Oda.query.filter_by(id=oda_id).first()
                if oda:
                    metric = MLMetric(
                        metric_type='talep_yogunluk',
                        entity_id=oda_id,
                        metric_value=float(talep_sayisi),
                        timestamp=timestamp,
                        extra_data={
                            'oda_no': oda.oda_no,
                            'kat': oda.kat.kat_adi if oda.kat else None
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ Talep metrikleri toplandı: {collected_count} kayıt")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Talep metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_qr_metrics(self):
        """
        QR okutma metriklerini topla
        Returns: Toplanan metrik sayısı
        """
        try:
            from models import QRKodOkutmaLog, Kullanici, MLMetric
            
            # Son 24 saatlik QR okutmalar
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Kat sorumluları
            kat_sorumlulari = Kullanici.query.filter_by(
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            
            collected_count = 0
            timestamp = datetime.now(timezone.utc)
            
            for personel in kat_sorumlulari:
                # Bu personelin son 24 saatteki QR okutma sayısı
                qr_count = QRKodOkutmaLog.query.filter(
                    QRKodOkutmaLog.kullanici_id == personel.id,
                    QRKodOkutmaLog.okutma_tarihi >= son_24_saat,
                    QRKodOkutmaLog.basarili == True
                ).count()
                
                if qr_count > 0:
                    metric = MLMetric(
                        metric_type='qr_okutma_siklik',
                        entity_id=personel.id,
                        metric_value=float(qr_count),
                        timestamp=timestamp,
                        extra_data={
                            'personel_adi': f"{personel.ad} {personel.soyad}",
                            'okutma_sayisi': qr_count
                        }
                    )
                    self.db.session.add(metric)
                    collected_count += 1
            
            self.db.session.commit()
            logger.info(f"✅ QR metrikleri toplandı: {collected_count} kayıt")
            return collected_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ QR metrik toplama hatası: {str(e)}")
            return 0
    
    def collect_all_metrics(self, save_features=True):
        """
        Tüm metrikleri topla
        Args:
            save_features: Feature'ları da kaydet mi? (varsayılan: True)
        Returns: Toplam toplanan metrik sayısı
        """
        try:
            logger.info("🔄 Veri toplama başladı...")
            
            stok_count = self.collect_stok_metrics()
            tuketim_count = self.collect_tuketim_metrics()
            dolum_count = self.collect_dolum_metrics()
            zimmet_count = self.collect_zimmet_metrics()
            occupancy_count = self.collect_occupancy_metrics()
            talep_count = self.collect_talep_metrics()
            qr_count = self.collect_qr_metrics()
            
            total_count = stok_count + tuketim_count + dolum_count + zimmet_count + occupancy_count + talep_count + qr_count
            
            logger.info(f"✅ Toplam {total_count} metrik toplandı")
            logger.info(f"   - Stok: {stok_count}")
            logger.info(f"   - Tüketim: {tuketim_count}")
            logger.info(f"   - Dolum: {dolum_count}")
            logger.info(f"   - Zimmet: {zimmet_count}")
            logger.info(f"   - Doluluk: {occupancy_count}")
            logger.info(f"   - Talep: {talep_count}")
            logger.info(f"   - QR: {qr_count}")
            
            # Feature'ları da kaydet (her 4 saatte bir - veri toplama 15 dk'da bir)
            if save_features:
                try:
                    from datetime import datetime
                    current_hour = datetime.now().hour
                    # Saat 0, 4, 8, 12, 16, 20'de feature kaydet
                    if current_hour % 4 == 0:
                        self._save_features_batch()
                except Exception as fe:
                    logger.warning(f"⚠️  Feature kaydetme atlandı: {str(fe)}")
            
            return total_count
            
        except Exception as e:
            logger.error(f"❌ Veri toplama hatası: {str(e)}")
            return 0
    
    def _save_features_batch(self):
        """Toplu feature kaydetme (stok için)"""
        try:
            from utils.ml.feature_engineer import FeatureEngineer
            from models import Urun
            
            engineer = FeatureEngineer(self.db)
            
            # Aktif ürünler için feature çıkar ve kaydet
            urunler = Urun.query.filter_by(aktif=True).limit(100).all()  # Max 100 ürün
            saved_count = 0
            
            for urun in urunler:
                try:
                    features = engineer.extract_stok_features(urun.id, lookback_days=30, save_to_db=True)
                    if features:
                        saved_count += 1
                except Exception:
                    continue
            
            if saved_count > 0:
                logger.info(f"📊 {saved_count} ürün için feature kaydedildi")
                
        except Exception as e:
            logger.warning(f"⚠️  Batch feature kaydetme hatası: {str(e)}")
    
    def cleanup_old_metrics(self, days=90):
        """
        Eski metrikleri temizle (90 günden eski)
        Args:
            days: Kaç günden eski veriler silinecek
        Returns: Silinen kayıt sayısı
        """
        try:
            from models import MLMetric
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            deleted_count = MLMetric.query.filter(
                MLMetric.timestamp < cutoff_date
            ).delete()
            
            self.db.session.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️  {deleted_count} eski metrik silindi ({days} günden eski)")
            
            return deleted_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Metrik temizleme hatası: {str(e)}")
            return 0
