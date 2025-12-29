"""
Anomaly Detector - ML Anomaly Detection System
Anomali tespit motoru: Z-Score ve Isolation Forest algoritmaları
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import numpy as np
import pickle
import logging

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Anomali tespit motoru"""
    
    def __init__(self, db):
        self.db = db
        
        # ModelManager instance oluştur
        from utils.ml.model_manager import ModelManager
        self.model_manager = ModelManager(db)
        
        # Fallback tracking
        self.fallback_count = 0
        self.total_detections = 0
        self.fallback_reasons = {
            'file_not_found': 0,
            'corrupt_file': 0,
            'load_error': 0,
            'prediction_error': 0
        }
    
    def calculate_severity(self, deviation_percent):
        """
        Sapma yüzdesine göre önem seviyesi belirle
        Args:
            deviation_percent: Sapma yüzdesi (mutlak değer)
        Returns: 'dusuk', 'orta', 'yuksek', 'kritik'
        """
        abs_deviation = abs(deviation_percent)
        
        if abs_deviation < 30:
            return 'dusuk'
        elif abs_deviation < 50:
            return 'orta'
        elif abs_deviation < 80:
            return 'yuksek'
        else:
            return 'kritik'
    
    def detect_with_zscore(self, values, threshold=3.0):
        """
        Z-Score metodu ile anomali tespiti
        Args:
            values: Değerler listesi
            threshold: Z-score eşik değeri (varsayılan 3.0 = %99.7)
        Returns: (is_anomaly, z_score, mean, std)
        """
        if len(values) < 3:
            return False, 0, 0, 0
        
        values_array = np.array(values)
        mean = np.mean(values_array)
        std = np.std(values_array)
        
        if std == 0:
            return False, 0, mean, 0
        
        current_value = values[-1]
        z_score = abs((current_value - mean) / std)
        
        is_anomaly = z_score > threshold
        
        return is_anomaly, z_score, mean, std
    
    def detect_with_model(self, metric_type: str, values: list):
        """
        Model ile anomali tespiti (fallback: Z-Score)
        
        Args:
            metric_type: Metrik tipi
            values: Değerler listesi
            
        Returns:
            tuple: (is_anomaly, z_score, mean, std) - Z-Score ile tutarlı format
        """
        self.total_detections += 1
        
        try:
            # Model yükle (dosyadan)
            model_package = self.model_manager.load_model_from_file(
                model_type='isolation_forest',
                metric_type=metric_type
            )
            
            if model_package is None:
                # Fallback: Z-Score kullan
                self.fallback_count += 1
                self.fallback_reasons['file_not_found'] += 1
                
                logger.warning(
                    f"⚠️  [FALLBACK_FILE_NOT_FOUND] Model bulunamadı, Z-Score fallback: {metric_type} | "
                    f"Fallback rate: {self._get_fallback_rate():.1f}%"
                )
                
                # Fallback oranı yüksekse alert oluştur
                self._check_fallback_rate_alert()
                
                return self.detect_with_zscore(values)
            
            # Model package'dan model ve scaler'ı çıkar
            try:
                # Yeni format: dict içinde model
                if isinstance(model_package, dict):
                    model = model_package.get('model')
                    scaler = model_package.get('scaler')
                else:
                    # Eski format: direkt model
                    model = model_package
                    scaler = None
                
                if model is None:
                    raise ValueError("Model package içinde model bulunamadı")
                
                # Veriyi hazırla
                values_array = np.array(values).reshape(-1, 1)
                
                # Scaler varsa uygula
                if scaler is not None:
                    values_array = scaler.transform(values_array)
                
                # Model ile tahmin yap
                predictions = model.predict(values_array)
                
                # İstatistikleri hesapla (Z-Score ile tutarlı return için)
                mean = float(np.mean(values))
                std = float(np.std(values))
                current_value = values[-1]
                z_score = abs((current_value - mean) / std) if std > 0 else 0
                
                # Modeli bellekten temizle
                del model_package
                
                # -1: anomali, 1: normal
                is_anomaly = predictions[-1] == -1
                
                return is_anomaly, z_score, mean, std
                
            except Exception as pred_error:
                # Prediction hatası - fallback
                self.fallback_count += 1
                self.fallback_reasons['prediction_error'] += 1
                
                logger.error(
                    f"❌ [FALLBACK_PREDICTION_ERROR] Model prediction hatası: {metric_type} | "
                    f"Error: {str(pred_error)} | "
                    f"Fallback rate: {self._get_fallback_rate():.1f}%"
                )
                
                # Model'i temizle
                try:
                    del model_package
                except:
                    pass
                
                # Fallback: Z-Score
                return self.detect_with_zscore(values)
            
        except FileNotFoundError as e:
            # Dosya bulunamadı
            self.fallback_count += 1
            self.fallback_reasons['file_not_found'] += 1
            
            logger.warning(
                f"⚠️  [FALLBACK_FILE_NOT_FOUND] Model dosyası bulunamadı: {metric_type} | "
                f"Fallback rate: {self._get_fallback_rate():.1f}%"
            )
            
            self._check_fallback_rate_alert()
            return self.detect_with_zscore(values)
            
        except (EOFError, pickle.UnpicklingError) as e:
            # Corrupt file
            self.fallback_count += 1
            self.fallback_reasons['corrupt_file'] += 1
            
            logger.error(
                f"❌ [FALLBACK_CORRUPT_FILE] Model dosyası bozuk: {metric_type} | "
                f"Error: {str(e)} | "
                f"Fallback rate: {self._get_fallback_rate():.1f}%"
            )
            
            self._check_fallback_rate_alert()
            return self.detect_with_zscore(values)
            
        except Exception as e:
            # Genel hata
            self.fallback_count += 1
            self.fallback_reasons['load_error'] += 1
            
            logger.error(
                f"❌ [FALLBACK_LOAD_ERROR] Model yükleme hatası: {metric_type} | "
                f"Error: {str(e)} | "
                f"Fallback rate: {self._get_fallback_rate():.1f}%"
            )
            
            self._check_fallback_rate_alert()
            return self.detect_with_zscore(values)
    
    def detect_stok_anomalies(self):
        """
        Stok seviyesi anomalilerini tespit et
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MLMetric, MLAlert, Urun
            
            # Son 30 günlük stok metriklerini al
            son_30_gun = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Aktif ürünleri al
            urunler = Urun.query.filter_by(aktif=True).all()
            
            alert_count = 0
            
            for urun in urunler:
                # Bu ürün için son 30 günlük metrikleri al
                metrikler = MLMetric.query.filter(
                    MLMetric.metric_type == 'stok_seviye',
                    MLMetric.entity_id == urun.id,
                    MLMetric.timestamp >= son_30_gun
                ).order_by(MLMetric.timestamp).all()
                
                if len(metrikler) < 1:
                    continue
                
                values = [m.metric_value for m in metrikler]
                current_value = values[-1]
                
                # 🚨 KRİTİK: NEGATİF STOK KONTROLÜ (En yüksek öncelik!)
                if current_value < 0:
                    # Negatif stok = KRİTİK anomali
                    # Son 1 saatte aynı ürün için alert var mı kontrol et
                    son_1_saat = datetime.now(timezone.utc) - timedelta(hours=1)
                    existing_alert = MLAlert.query.filter(
                        MLAlert.alert_type == 'stok_anomali',
                        MLAlert.entity_type == 'urun',
                        MLAlert.entity_id == urun.id,
                        MLAlert.created_at >= son_1_saat,
                        MLAlert.is_false_positive == False
                    ).first()
                    
                    if not existing_alert:
                        message = f"🚨 NEGATİF STOK: {urun.urun_adi} - Mevcut stok: {int(current_value)}"
                        suggested_action = f"ACİL: Stok hareketlerini kontrol edin. Veri tutarsızlığı var!"
                        
                        alert = MLAlert(
                            alert_type='stok_anomali',
                            severity='kritik',
                            entity_type='urun',
                            entity_id=urun.id,
                            metric_value=current_value,
                            expected_value=0,
                            deviation_percent=100,
                            message=message,
                            suggested_action=suggested_action
                        )
                        self.db.session.add(alert)
                        alert_count += 1
                        logger.warning(f"⚠️  NEGATİF STOK ALERT: {urun.urun_adi} = {int(current_value)}")
                    
                    continue  # Negatif stok için Z-Score kontrolüne gerek yok
                
                # Normal Z-Score anomali tespiti (sadece pozitif stoklar için)
                if len(metrikler) < 3:
                    continue
                
                # Z-Score ile anomali tespiti
                is_anomaly, z_score, mean, std = self.detect_with_zscore(values)
                
                if is_anomaly:
                    current_value = values[-1]
                    deviation_percent = ((current_value - mean) / mean * 100) if mean > 0 else 0
                    severity = self.calculate_severity(deviation_percent)
                    
                    # Aynı ürün için son 1 saatte alert var mı kontrol et
                    son_1_saat = datetime.now(timezone.utc) - timedelta(hours=1)
                    existing_alert = MLAlert.query.filter(
                        MLAlert.alert_type == 'stok_anomali',
                        MLAlert.entity_id == urun.id,
                        MLAlert.created_at >= son_1_saat,
                        MLAlert.is_false_positive == False
                    ).first()
                    
                    if not existing_alert:
                        # Mesaj oluştur
                        if current_value < mean:
                            message = f"{urun.urun_adi} stok seviyesi normalden %{abs(deviation_percent):.1f} düşük (Mevcut: {int(current_value)}, Beklenen: {int(mean)})"
                            suggested_action = f"Acil sipariş verin. Kritik seviye: {urun.kritik_stok_seviyesi}"
                        else:
                            message = f"{urun.urun_adi} stok seviyesi normalden %{abs(deviation_percent):.1f} yüksek (Mevcut: {int(current_value)}, Beklenen: {int(mean)})"
                            suggested_action = "Stok kontrolü yapın. Fazla stok olabilir."
                        
                        # Alert oluştur
                        alert = MLAlert(
                            alert_type='stok_anomali',
                            severity=severity,
                            entity_type='urun',
                            entity_id=urun.id,
                            metric_value=current_value,
                            expected_value=mean,
                            deviation_percent=deviation_percent,
                            message=message,
                            suggested_action=suggested_action
                        )
                        self.db.session.add(alert)
                        alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} stok anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Stok anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_tuketim_anomalies(self):
        """
        Tüketim anomalilerini tespit et (oda bazlı)
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MLMetric, MLAlert, Oda
            
            # Son 7 günlük tüketim metriklerini al
            son_7_gun = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Aktif odaları al
            odalar = Oda.query.filter_by(aktif=True).all()
            
            alert_count = 0
            
            for oda in odalar:
                # Bu oda için son 7 günlük metrikleri al (tuketim_oran - DataCollector ile uyumlu)
                metrikler = MLMetric.query.filter(
                    MLMetric.metric_type.in_(['tuketim_oran', 'tuketim_miktar', 'minibar_tuketim']),
                    MLMetric.entity_id == oda.id,
                    MLMetric.timestamp >= son_7_gun
                ).order_by(MLMetric.timestamp).all()
                
                if len(metrikler) < 3:
                    continue
                
                values = [m.metric_value for m in metrikler]
                
                # Z-Score ile anomali tespiti (daha düşük threshold: 2.5)
                is_anomaly, z_score, mean, std = self.detect_with_zscore(values, threshold=2.5)
                
                if is_anomaly:
                    current_value = values[-1]
                    deviation_percent = ((current_value - mean) / mean * 100) if mean > 0 else 0
                    
                    # %40'tan fazla sapma varsa alert oluştur
                    if abs(deviation_percent) >= 40:
                        severity = self.calculate_severity(deviation_percent)
                        
                        # Aynı oda için son 6 saatte alert var mı kontrol et
                        son_6_saat = datetime.now(timezone.utc) - timedelta(hours=6)
                        existing_alert = MLAlert.query.filter(
                            MLAlert.alert_type == 'tuketim_anomali',
                            MLAlert.entity_id == oda.id,
                            MLAlert.created_at >= son_6_saat,
                            MLAlert.is_false_positive == False
                        ).first()
                        
                        if not existing_alert:
                            # Mesaj oluştur
                            if current_value > mean:
                                message = f"Oda {oda.oda_no} tüketimi normalden %{abs(deviation_percent):.1f} yüksek (Günlük: {int(current_value)}, Ortalama: {int(mean)})"
                                suggested_action = "Minibar kontrolü yapın. Olağandışı tüketim var."
                            else:
                                message = f"Oda {oda.oda_no} tüketimi normalden %{abs(deviation_percent):.1f} düşük (Günlük: {int(current_value)}, Ortalama: {int(mean)})"
                                suggested_action = "Oda boş olabilir veya minibar kullanılmıyor."
                            
                            # Alert oluştur
                            alert = MLAlert(
                                alert_type='tuketim_anomali',
                                severity=severity,
                                entity_type='oda',
                                entity_id=oda.id,
                                metric_value=current_value,
                                expected_value=mean,
                                deviation_percent=deviation_percent,
                                message=message,
                                suggested_action=suggested_action
                            )
                            self.db.session.add(alert)
                            alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} tüketim anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Tüketim anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_dolum_anomalies(self):
        """
        Dolum süresi anomalilerini tespit et
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MLMetric, MLAlert, Kullanici
            
            # Son 7 günlük dolum metriklerini al
            son_7_gun = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Kat sorumluları
            kat_sorumlulari = Kullanici.query.filter_by(
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            
            alert_count = 0
            
            for personel in kat_sorumlulari:
                # Bu personel için son 7 günlük metrikleri al
                metrikler = MLMetric.query.filter(
                    MLMetric.metric_type == 'dolum_sure',
                    MLMetric.entity_id == personel.id,
                    MLMetric.timestamp >= son_7_gun
                ).order_by(MLMetric.timestamp).all()
                
                if len(metrikler) < 3:
                    continue
                
                values = [m.metric_value for m in metrikler]
                
                # Z-Score ile anomali tespiti
                is_anomaly, z_score, mean, std = self.detect_with_zscore(values, threshold=2.0)
                
                if is_anomaly:
                    current_value = values[-1]
                    deviation_percent = ((current_value - mean) / mean * 100) if mean > 0 else 0
                    
                    # %50'den fazla uzun sürüyorsa alert oluştur
                    if deviation_percent >= 50:
                        severity = self.calculate_severity(deviation_percent)
                        
                        # Aynı personel için son 12 saatte alert var mı kontrol et
                        son_12_saat = datetime.now(timezone.utc) - timedelta(hours=12)
                        existing_alert = MLAlert.query.filter(
                            MLAlert.alert_type == 'dolum_gecikme',
                            MLAlert.entity_id == personel.id,
                            MLAlert.created_at >= son_12_saat,
                            MLAlert.is_false_positive == False
                        ).first()
                        
                        if not existing_alert:
                            # Mesaj oluştur
                            message = f"{personel.ad} {personel.soyad} dolum süresi normalden %{abs(deviation_percent):.1f} uzun (Mevcut: {int(current_value)} dk, Ortalama: {int(mean)} dk)"
                            suggested_action = "Personel ile görüşün. Operasyonel sorun olabilir."
                            
                            # Alert oluştur
                            alert = MLAlert(
                                alert_type='dolum_gecikme',
                                severity=severity,
                                entity_type='personel',
                                entity_id=personel.id,
                                metric_value=current_value,
                                expected_value=mean,
                                deviation_percent=deviation_percent,
                                message=message,
                                suggested_action=suggested_action
                            )
                            self.db.session.add(alert)
                            alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} dolum süresi anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Dolum süresi anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_zimmet_anomalies(self):
        """
        Zimmet fire ve kullanım anomalilerini tespit et
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MLMetric, MLAlert, Kullanici
            
            # Son 7 günlük zimmet metriklerini al
            son_7_gun = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Kat sorumluları
            kat_sorumlulari = Kullanici.query.filter_by(
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            
            alert_count = 0
            
            for personel in kat_sorumlulari:
                # Fire oranı metriklerini al
                fire_metrikler = MLMetric.query.filter(
                    MLMetric.metric_type == 'zimmet_fire',
                    MLMetric.entity_id == personel.id,
                    MLMetric.timestamp >= son_7_gun
                ).order_by(MLMetric.timestamp).all()
                
                if len(fire_metrikler) >= 2:
                    son_fire = fire_metrikler[-1].metric_value
                    
                    # %20+ fire oranı varsa alert
                    if son_fire >= 20:
                        # Son 24 saatte aynı personel için alert var mı?
                        son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
                        existing_alert = MLAlert.query.filter(
                            MLAlert.alert_type == 'zimmet_fire_yuksek',
                            MLAlert.entity_id == personel.id,
                            MLAlert.created_at >= son_24_saat,
                            MLAlert.is_false_positive == False
                        ).first()
                        
                        if not existing_alert:
                            # Severity belirle
                            if son_fire >= 40:
                                severity = 'kritik'
                            elif son_fire >= 30:
                                severity = 'yuksek'
                            else:
                                severity = 'orta'
                            
                            message = f"{personel.ad} {personel.soyad} zimmet fire oranı %{son_fire:.1f}"
                            suggested_action = "Zimmet kontrolü yapın. Kayıp/fire nedenlerini araştırın."
                            
                            alert = MLAlert(
                                alert_type='zimmet_fire_yuksek',
                                severity=severity,
                                entity_type='personel',
                                entity_id=personel.id,
                                metric_value=son_fire,
                                expected_value=10.0,  # Beklenen fire oranı %10
                                deviation_percent=((son_fire - 10) / 10 * 100),
                                message=message,
                                suggested_action=suggested_action
                            )
                            self.db.session.add(alert)
                            alert_count += 1
                
                # Kullanım oranı metriklerini al
                kullanim_metrikler = MLMetric.query.filter(
                    MLMetric.metric_type == 'zimmet_kullanim',
                    MLMetric.entity_id == personel.id,
                    MLMetric.timestamp >= son_7_gun
                ).order_by(MLMetric.timestamp).all()
                
                if len(kullanim_metrikler) >= 2:
                    son_kullanim = kullanim_metrikler[-1].metric_value
                    
                    # %30'dan az kullanım varsa alert
                    if son_kullanim < 30:
                        son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
                        existing_alert = MLAlert.query.filter(
                            MLAlert.alert_type == 'zimmet_fire_yuksek',  # Düzeltildi: zimmet_kullanim_dusuk kaldırıldı
                            MLAlert.entity_id == personel.id,
                            MLAlert.created_at >= son_24_saat,
                            MLAlert.is_false_positive == False
                        ).first()
                        
                        if not existing_alert:
                            severity = 'orta'
                            message = f"{personel.ad} {personel.soyad} zimmet kullanım oranı düşük (%{son_kullanim:.1f})"
                            suggested_action = "Zimmet kullanımını kontrol edin. Fazla zimmet verilmiş olabilir."
                            
                            alert = MLAlert(
                                alert_type='zimmet_fire_yuksek',  # Düzeltildi: zimmet_kullanim_dusuk kaldırıldı
                                severity=severity,
                                entity_type='personel',
                                entity_id=personel.id,
                                metric_value=son_kullanim,
                                expected_value=70.0,
                                deviation_percent=((70 - son_kullanim) / 70 * 100),
                                message=message,
                                suggested_action=suggested_action
                            )
                            self.db.session.add(alert)
                            alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} zimmet anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Zimmet anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_occupancy_anomalies(self):
        """
        Doluluk anomalilerini tespit et (boş oda tüketim)
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MLMetric, MLAlert, Oda
            
            # Son 24 saatlik boş oda tüketim metriklerini al
            son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
            
            metrikler = MLMetric.query.filter(
                MLMetric.metric_type == 'bosta_tuketim',
                MLMetric.timestamp >= son_24_saat
            ).all()
            
            alert_count = 0
            
            for metrik in metrikler:
                # Bu oda için son 6 saatte alert var mı?
                son_6_saat = datetime.now(timezone.utc) - timedelta(hours=6)
                existing_alert = MLAlert.query.filter(
                    MLAlert.alert_type == 'bosta_tuketim_var',
                    MLAlert.entity_id == metrik.entity_id,
                    MLAlert.created_at >= son_6_saat,
                    MLAlert.is_false_positive == False
                ).first()
                
                if not existing_alert:
                    oda = Oda.query.filter_by(id=metrik.entity_id).first()
                    if not oda:
                        continue
                    
                    # Boş oda ama tüketim var = KRİTİK (hırsızlık olabilir!)
                    severity = 'kritik'
                    message = f"Oda {oda.oda_no} BOŞ ama tüketim var! ({int(metrik.metric_value)} ürün)"
                    suggested_action = "ACİL güvenlik kontrolü yapın! Hırsızlık veya yetkisiz giriş olabilir."
                    
                    alert = MLAlert(
                        alert_type='bosta_tuketim_var',
                        severity=severity,
                        entity_type='oda',
                        entity_id=metrik.entity_id,
                        metric_value=metrik.metric_value,
                        expected_value=0.0,
                        deviation_percent=100.0,
                        message=message,
                        suggested_action=suggested_action
                    )
                    self.db.session.add(alert)
                    alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} doluluk anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Doluluk anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_talep_anomalies(self):
        """
        Talep anomalilerini tespit et
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MinibarDolumTalebi, MLAlert, Oda
            
            # Bekleyen talepler (30 dakikadan uzun)
            otuz_dakika_once = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            bekleyen_talepler = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.durum == 'beklemede',
                MinibarDolumTalebi.talep_tarihi <= otuz_dakika_once
            ).all()
            
            alert_count = 0
            
            for talep in bekleyen_talepler:
                # Bu talep için son 1 saatte alert var mı?
                son_1_saat = datetime.now(timezone.utc) - timedelta(hours=1)
                existing_alert = MLAlert.query.filter(
                    MLAlert.alert_type == 'talep_yanitlanmadi',
                    MLAlert.entity_id == talep.oda_id,
                    MLAlert.created_at >= son_1_saat,
                    MLAlert.is_false_positive == False
                ).first()
                
                if not existing_alert:
                    bekle_sure = (datetime.now(timezone.utc) - talep.talep_tarihi).total_seconds() / 60
                    
                    # Severity belirle
                    if bekle_sure >= 120:  # 2 saat
                        severity = 'kritik'
                    elif bekle_sure >= 60:  # 1 saat
                        severity = 'yuksek'
                    else:
                        severity = 'orta'
                    
                    oda = Oda.query.filter_by(id=talep.oda_id).first()
                    message = f"Oda {oda.oda_no if oda else talep.oda_id} dolum talebi {int(bekle_sure)} dakikadır bekliyor"
                    suggested_action = "Kat sorumlusuna bildirim gönderin. Misafir memnuniyetsizliği riski var."
                    
                    alert = MLAlert(
                        alert_type='talep_yanitlanmadi',
                        severity=severity,
                        entity_type='oda',
                        entity_id=talep.oda_id,
                        metric_value=bekle_sure,
                        expected_value=15.0,  # Beklenen yanıt süresi 15 dakika
                        deviation_percent=((bekle_sure - 15) / 15 * 100),
                        message=message,
                        suggested_action=suggested_action
                    )
                    self.db.session.add(alert)
                    alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} talep anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ Talep anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_qr_anomalies(self):
        """
        QR kullanım anomalilerini tespit et
        Returns: Oluşturulan alert sayısı
        """
        try:
            from models import MLMetric, MLAlert, Kullanici
            
            # Son 7 günlük QR metriklerini al
            son_7_gun = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Kat sorumluları
            kat_sorumlulari = Kullanici.query.filter_by(
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            
            alert_count = 0
            
            for personel in kat_sorumlulari:
                # Son 7 günlük QR okutma metrikleri
                qr_metrikler = MLMetric.query.filter(
                    MLMetric.metric_type == 'qr_okutma_siklik',
                    MLMetric.entity_id == personel.id,
                    MLMetric.timestamp >= son_7_gun
                ).all()
                
                if len(qr_metrikler) >= 3:
                    ortalama = sum([m.metric_value for m in qr_metrikler]) / len(qr_metrikler)
                    son_deger = qr_metrikler[-1].metric_value
                    
                    # Ortalamadan %50 az QR okutma varsa
                    if ortalama > 5 and son_deger < (ortalama * 0.5):
                        # Son 24 saatte alert var mı?
                        son_24_saat = datetime.now(timezone.utc) - timedelta(hours=24)
                        existing_alert = MLAlert.query.filter(
                            MLAlert.alert_type == 'qr_kullanim_dusuk',
                            MLAlert.entity_id == personel.id,
                            MLAlert.created_at >= son_24_saat,
                            MLAlert.is_false_positive == False
                        ).first()
                        
                        if not existing_alert:
                            severity = 'orta'
                            message = f"{personel.ad} {personel.soyad} QR sistemi kullanımı düşük (Bugün: {int(son_deger)}, Ortalama: {int(ortalama)})"
                            suggested_action = "QR sistemi kullanımını teşvik edin. Manuel işlem yerine QR okutma daha güvenli."
                            
                            alert = MLAlert(
                                alert_type='qr_kullanim_dusuk',
                                severity=severity,
                                entity_type='personel',
                                entity_id=personel.id,
                                metric_value=son_deger,
                                expected_value=ortalama,
                                deviation_percent=((ortalama - son_deger) / ortalama * 100),
                                message=message,
                                suggested_action=suggested_action
                            )
                            self.db.session.add(alert)
                            alert_count += 1
            
            self.db.session.commit()
            
            if alert_count > 0:
                logger.info(f"⚠️  {alert_count} QR anomalisi tespit edildi")
            
            return alert_count
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"❌ QR anomali tespiti hatası: {str(e)}")
            return 0
    
    def detect_all_anomalies(self):
        """
        Tüm anomali tiplerini tespit et
        Returns: Toplam oluşturulan alert sayısı
        """
        try:
            logger.info("🔍 Anomali tespiti başladı...")
            
            stok_count = self.detect_stok_anomalies()
            tuketim_count = self.detect_tuketim_anomalies()
            dolum_count = self.detect_dolum_anomalies()
            zimmet_count = self.detect_zimmet_anomalies()
            occupancy_count = self.detect_occupancy_anomalies()
            talep_count = self.detect_talep_anomalies()
            qr_count = self.detect_qr_anomalies()
            
            total_count = stok_count + tuketim_count + dolum_count + zimmet_count + occupancy_count + talep_count + qr_count
            
            if total_count > 0:
                logger.info(f"⚠️  Toplam {total_count} anomali tespit edildi")
                logger.info(f"   - Stok: {stok_count}")
                logger.info(f"   - Tüketim: {tuketim_count}")
                logger.info(f"   - Dolum: {dolum_count}")
                logger.info(f"   - Zimmet: {zimmet_count}")
                logger.info(f"   - Doluluk: {occupancy_count}")
                logger.info(f"   - Talep: {talep_count}")
                logger.info(f"   - QR: {qr_count}")
            else:
                logger.info("✅ Anomali tespit edilmedi")
            
            # Fallback istatistiklerini logla
            fallback_stats = self.get_fallback_stats()
            if fallback_stats['total_detections'] > 0:
                logger.info(
                    f"📊 [FALLBACK_STATS] Fallback kullanımı: {fallback_stats['fallback_rate']:.1f}% | "
                    f"Total: {fallback_stats['total_detections']} | "
                    f"Fallback: {fallback_stats['fallback_count']} | "
                    f"Status: {fallback_stats['status']}"
                )
            
            return total_count
            
        except Exception as e:
            logger.error(f"❌ Anomali tespiti hatası: {str(e)}")
            return 0

    def _get_fallback_rate(self) -> float:
        """
        Fallback kullanım oranını hesapla
        
        Returns:
            float: Fallback oranı (%)
        """
        if self.total_detections == 0:
            return 0.0
        return (self.fallback_count / self.total_detections) * 100
    
    def _check_fallback_rate_alert(self):
        """
        Fallback oranı yüksekse kritik alert oluştur
        """
        fallback_rate = self._get_fallback_rate()
        
        # %50'den fazla fallback kullanılıyorsa kritik alert
        if fallback_rate > 50 and self.total_detections >= 10:
            try:
                from models import MLAlert
                
                # Son 1 saatte aynı alert var mı kontrol et
                son_1_saat = datetime.now(timezone.utc) - timedelta(hours=1)
                existing_alert = MLAlert.query.filter(
                    MLAlert.alert_type == 'stok_anomali',  # En yakın tip
                    MLAlert.entity_id == 0,  # Sistem seviyesi
                    MLAlert.message.like('%Fallback%'),
                    MLAlert.created_at >= son_1_saat
                ).first()
                
                if existing_alert:
                    return  # Zaten alert var
                
                # Yeni alert oluştur
                alert = MLAlert(
                    alert_type='stok_anomali',
                    severity='kritik',
                    entity_type='sistem',
                    entity_id=0,  # Sistem seviyesi
                    metric_value=fallback_rate,
                    expected_value=10.0,
                    deviation_percent=(fallback_rate - 10.0) / 10.0 * 100,
                    message=f"ML Model Fallback oranı kritik seviyede: {fallback_rate:.1f}%",
                    suggested_action=(
                        f"Model dosyaları kontrol edilmeli. "
                        f"Fallback sebepleri: "
                        f"File not found: {self.fallback_reasons['file_not_found']}, "
                        f"Corrupt file: {self.fallback_reasons['corrupt_file']}, "
                        f"Load error: {self.fallback_reasons['load_error']}, "
                        f"Prediction error: {self.fallback_reasons['prediction_error']}"
                    ),
                    created_at=datetime.now(timezone.utc)
                )
                
                self.db.session.add(alert)
                self.db.session.commit()
                
                logger.critical(
                    f"🚨 [CRITICAL_FALLBACK_RATE] Fallback oranı kritik: {fallback_rate:.1f}% | "
                    f"Total detections: {self.total_detections} | "
                    f"Fallback count: {self.fallback_count}"
                )
                
            except Exception as e:
                logger.error(f"❌ Fallback alert oluşturma hatası: {str(e)}")
                self.db.session.rollback()
    
    def get_fallback_stats(self) -> dict:
        """
        Fallback istatistiklerini getir
        
        Returns:
            dict: Fallback istatistikleri
        """
        return {
            'total_detections': self.total_detections,
            'fallback_count': self.fallback_count,
            'fallback_rate': round(self._get_fallback_rate(), 2),
            'fallback_reasons': self.fallback_reasons.copy(),
            'status': 'critical' if self._get_fallback_rate() > 50 else 
                     'warning' if self._get_fallback_rate() > 20 else 'ok'
        }
    
    def reset_fallback_stats(self):
        """Fallback istatistiklerini sıfırla"""
        self.fallback_count = 0
        self.total_detections = 0
        self.fallback_reasons = {
            'file_not_found': 0,
            'corrupt_file': 0,
            'load_error': 0,
            'prediction_error': 0
        }
        logger.info("📊 Fallback istatistikleri sıfırlandı")
