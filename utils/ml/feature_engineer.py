"""
Feature Engineering - ML Anomaly Detection System
Ham verilerden anlamlı özellikler (features) çıkarır
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Feature engineering servisi"""
    
    def __init__(self, db):
        self.db = db
    
    def save_features_to_db(self, metric_type, entity_id, features_dict, timestamp=None):
        """
        Feature'ları veritabanına kaydet
        
        Args:
            metric_type: Metrik tipi (stok_seviye, tuketim_miktar, vb.)
            entity_id: Entity ID (urun_id, oda_id, vb.)
            features_dict: Feature dictionary
            timestamp: Zaman damgası (None ise şimdi)
        
        Returns:
            MLFeature instance veya None
        """
        try:
            from models import MLFeature
            
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Feature mapping
            feature = MLFeature(
                metric_type=metric_type,
                entity_id=entity_id,
                timestamp=timestamp,
                
                # Statistical
                mean_value=features_dict.get('mean'),
                std_value=features_dict.get('std'),
                min_value=features_dict.get('min'),
                max_value=features_dict.get('max'),
                median_value=features_dict.get('median'),
                q25_value=features_dict.get('q25'),
                q75_value=features_dict.get('q75'),
                
                # Trend
                trend_slope=features_dict.get('slope'),
                trend_direction=features_dict.get('trend'),
                volatility=features_dict.get('volatility'),
                momentum=features_dict.get('change_rate'),
                
                # Time
                hour_of_day=timestamp.hour,
                day_of_week=timestamp.weekday(),
                is_weekend=(timestamp.weekday() >= 5),
                day_of_month=timestamp.day,
                
                # Domain Specific
                days_since_last_change=features_dict.get('days_since_last_change'),
                change_frequency=features_dict.get('change_frequency'),
                avg_change_magnitude=features_dict.get('avg_change'),
                zero_count=features_dict.get('zero_count', 0),
                
                # Lag
                lag_1=features_dict.get('lag_1'),
                lag_7=features_dict.get('lag_7'),
                lag_30=features_dict.get('lag_30'),
                
                # Rolling
                rolling_mean_7=features_dict.get('rolling_mean_7'),
                rolling_std_7=features_dict.get('rolling_std_7'),
                rolling_mean_30=features_dict.get('rolling_mean_30'),
                rolling_std_30=features_dict.get('rolling_std_30'),
                
                # Extra features (diğer tüm feature'lar)
                extra_features={
                    k: v for k, v in features_dict.items()
                    if k not in ['mean', 'std', 'min', 'max', 'median', 'q25', 'q75',
                                 'slope', 'trend', 'volatility', 'change_rate',
                                 'days_since_last_change', 'change_frequency', 'avg_change',
                                 'lag_1', 'lag_7', 'lag_30',
                                 'rolling_mean_7', 'rolling_std_7', 'rolling_mean_30', 'rolling_std_30']
                }
            )
            
            self.db.session.add(feature)
            self.db.session.commit()
            
            logger.info(f"✅ Feature kaydedildi: {metric_type} - Entity #{entity_id}")
            return feature
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Feature kaydetme hatası: {str(e)}")
            return None
    
    def extract_stok_features(self, urun_id, lookback_days=30, save_to_db=True):
        """
        Stok verileri için feature'lar çıkar
        
        Args:
            urun_id: Ürün ID
            lookback_days: Kaç günlük veri kullanılacak
            save_to_db: Feature'ları veritabanına kaydet mi?
        
        Features:
        - Ortalama stok seviyesi
        - Stok volatilitesi (std)
        - Trend (artış/azalış)
        - Değişim hızı
        - Min/Max değerler
        - Kritik seviyeye yakınlık
        """
        try:
            from models import MLMetric, Urun
            
            # Son N günlük stok metrikleri
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            metrics = MLMetric.query.filter(
                MLMetric.metric_type == 'stok_seviye',
                MLMetric.entity_id == urun_id,
                MLMetric.timestamp >= cutoff_date
            ).order_by(MLMetric.timestamp.asc()).all()
            
            if len(metrics) < 2:
                return None
            
            # Değerleri al
            values = np.array([m.metric_value for m in metrics])
            timestamps = [m.timestamp for m in metrics]
            
            # Ürün bilgisi
            urun = Urun.query.get(urun_id)
            kritik_seviye = urun.kritik_stok_seviyesi if urun else 0
            
            # Feature'lar
            features = {
                # İstatistiksel özellikler
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'median': float(np.median(values)),
                'q25': float(np.percentile(values, 25)),
                'q75': float(np.percentile(values, 75)),
                
                # Trend özellikleri
                'trend': self._calculate_trend(values),
                'slope': self._calculate_slope(timestamps, values),
                'volatility': float(np.std(values) / (np.mean(values) + 1e-6)),  # Coefficient of variation
                
                # Değişim özellikleri
                'change_rate': float((values[-1] - values[0]) / (values[0] + 1e-6)),
                'avg_change': float(np.mean(np.diff(values))),
                'max_change': float(np.max(np.abs(np.diff(values)))),
                
                # Kritik seviye özellikleri
                'distance_to_critical': float(values[-1] - kritik_seviye),
                'critical_ratio': float(values[-1] / (kritik_seviye + 1e-6)),
                'below_critical_count': int(np.sum(values <= kritik_seviye)),
                'below_critical_ratio': float(np.sum(values <= kritik_seviye) / len(values)),
                
                # Zaman özellikleri
                'days_of_data': lookback_days,
                'data_points': len(metrics),
                'data_density': float(len(metrics) / lookback_days),
                
                # Son değer
                'current_value': float(values[-1]),
                'previous_value': float(values[-2] if len(values) > 1 else values[-1]),
                
                # Anomali skorları
                'z_score': self._calculate_z_score(values[-1], values),
                'iqr_score': self._calculate_iqr_score(values[-1], values),
            }
            
            # Veritabanına kaydet
            if save_to_db:
                self.save_features_to_db('stok_seviye', urun_id, features, timestamps[-1])
            
            return features
            
        except Exception as e:
            logger.error(f"Stok feature extraction hatası: {str(e)}")
            return None
    
    def extract_tuketim_features(self, oda_id, lookback_days=30):
        """
        Tüketim verileri için feature'lar çıkar
        
        Features:
        - Ortalama tüketim
        - Tüketim patternleri
        - Hafta içi/sonu farkı
        - Trend
        - Seasonality
        """
        try:
            from models import MLMetric, Oda, MisafirKayit
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            metrics = MLMetric.query.filter(
                MLMetric.metric_type.in_(['tuketim_oran', 'minibar_tuketim']),
                MLMetric.entity_id == oda_id,
                MLMetric.timestamp >= cutoff_date
            ).order_by(MLMetric.timestamp.asc()).all()
            
            if len(metrics) < 2:
                return None
            
            values = np.array([m.metric_value for m in metrics])
            timestamps = [m.timestamp for m in metrics]
            
            # Oda bilgisi
            oda = Oda.query.get(oda_id)
            
            # Doluluk bilgisi
            doluluk_count = MisafirKayit.query.filter(
                MisafirKayit.oda_id == oda_id,
                MisafirKayit.giris_tarihi >= cutoff_date.date()
            ).count()
            
            # Hafta içi/sonu ayrımı
            weekday_values = []
            weekend_values = []
            
            for ts, val in zip(timestamps, values):
                if ts.weekday() < 5:  # Pazartesi-Cuma
                    weekday_values.append(val)
                else:  # Cumartesi-Pazar
                    weekend_values.append(val)
            
            features = {
                # Temel istatistikler
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'median': float(np.median(values)),
                
                # Trend
                'trend': self._calculate_trend(values),
                'slope': self._calculate_slope(timestamps, values),
                
                # Hafta içi/sonu
                'weekday_mean': float(np.mean(weekday_values)) if weekday_values else 0,
                'weekend_mean': float(np.mean(weekend_values)) if weekend_values else 0,
                'weekday_weekend_ratio': float(np.mean(weekday_values) / (np.mean(weekend_values) + 1e-6)) if weekday_values and weekend_values else 1,
                
                # Doluluk ilişkisi
                'occupancy_count': doluluk_count,
                'consumption_per_occupancy': float(np.sum(values) / (doluluk_count + 1e-6)),
                
                # Pattern özellikleri
                'consistency': 1.0 - float(np.std(values) / (np.mean(values) + 1e-6)),
                'peak_to_avg_ratio': float(np.max(values) / (np.mean(values) + 1e-6)),
                
                # Zaman özellikleri
                'days_of_data': lookback_days,
                'data_points': len(metrics),
                
                # Son değer
                'current_value': float(values[-1]),
                'z_score': self._calculate_z_score(values[-1], values),
                
                # Oda özellikleri
                'oda_tipi': oda.oda_tipi if oda else 'unknown',
                'kat_id': oda.kat_id if oda else 0,
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Tüketim feature extraction hatası: {str(e)}")
            return None
    
    def extract_dolum_features(self, personel_id, lookback_days=30):
        """
        Dolum süresi için feature'lar çıkar
        
        Features:
        - Ortalama dolum süresi
        - Süre varyasyonu
        - Verimlilik trendi
        - Zaman dilimi analizi
        """
        try:
            from models import MLMetric, Kullanici
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            metrics = MLMetric.query.filter(
                MLMetric.metric_type == 'dolum_sure',
                MLMetric.entity_id == personel_id,
                MLMetric.timestamp >= cutoff_date
            ).order_by(MLMetric.timestamp.asc()).all()
            
            if len(metrics) < 2:
                return None
            
            values = np.array([m.metric_value for m in metrics])
            timestamps = [m.timestamp for m in metrics]
            
            # Personel bilgisi
            personel = Kullanici.query.get(personel_id)
            
            # Zaman dilimi analizi (sabah/öğle/akşam)
            morning_values = []  # 06:00-12:00
            afternoon_values = []  # 12:00-18:00
            evening_values = []  # 18:00-24:00
            
            for ts, val in zip(timestamps, values):
                hour = ts.hour
                if 6 <= hour < 12:
                    morning_values.append(val)
                elif 12 <= hour < 18:
                    afternoon_values.append(val)
                elif 18 <= hour < 24:
                    evening_values.append(val)
            
            features = {
                # Temel istatistikler
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'median': float(np.median(values)),
                
                # Verimlilik
                'efficiency_score': float(1.0 / (np.mean(values) + 1e-6)),  # Düşük süre = yüksek verimlilik
                'consistency': 1.0 - float(np.std(values) / (np.mean(values) + 1e-6)),
                
                # Trend
                'trend': self._calculate_trend(values),
                'improvement_rate': -self._calculate_slope(timestamps, values),  # Negatif slope = iyileşme
                
                # Zaman dilimi analizi
                'morning_mean': float(np.mean(morning_values)) if morning_values else 0,
                'afternoon_mean': float(np.mean(afternoon_values)) if afternoon_values else 0,
                'evening_mean': float(np.mean(evening_values)) if evening_values else 0,
                
                # Performans metrikleri
                'fast_operations_ratio': float(np.sum(values < np.median(values)) / len(values)),
                'slow_operations_ratio': float(np.sum(values > np.percentile(values, 75)) / len(values)),
                
                # Zaman özellikleri
                'days_of_data': lookback_days,
                'data_points': len(metrics),
                'operations_per_day': float(len(metrics) / lookback_days),
                
                # Son değer
                'current_value': float(values[-1]),
                'z_score': self._calculate_z_score(values[-1], values),
                
                # Personel özellikleri
                'personel_adi': f"{personel.ad} {personel.soyad}" if personel else 'unknown',
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Dolum feature extraction hatası: {str(e)}")
            return None
    
    def extract_temporal_features(self, timestamp):
        """
        Zaman bazlı feature'lar çıkar
        
        Features:
        - Saat, gün, ay
        - Hafta içi/sonu
        - Tatil günü
        - Sezon
        """
        features = {
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'day_of_month': timestamp.day,
            'month': timestamp.month,
            'quarter': (timestamp.month - 1) // 3 + 1,
            'is_weekend': int(timestamp.weekday() >= 5),
            'is_weekday': int(timestamp.weekday() < 5),
            'is_morning': int(6 <= timestamp.hour < 12),
            'is_afternoon': int(12 <= timestamp.hour < 18),
            'is_evening': int(18 <= timestamp.hour < 24),
            'is_night': int(0 <= timestamp.hour < 6),
            'season': self._get_season(timestamp.month),
        }
        
        return features
    
    def create_feature_matrix(self, metric_type, entity_ids=None, lookback_days=30):
        """
        Birden fazla entity için feature matrix oluştur
        
        Returns: pandas DataFrame
        """
        try:
            from models import MLMetric
            
            if entity_ids is None:
                # Tüm entity'leri al
                entity_ids = self.db.session.query(
                    MLMetric.entity_id
                ).filter(
                    MLMetric.metric_type == metric_type
                ).distinct().all()
                entity_ids = [e[0] for e in entity_ids]
            
            features_list = []
            
            for entity_id in entity_ids:
                if metric_type == 'stok_seviye':
                    features = self.extract_stok_features(entity_id, lookback_days)
                elif metric_type in ['tuketim_oran', 'minibar_tuketim']:
                    features = self.extract_tuketim_features(entity_id, lookback_days)
                elif metric_type == 'dolum_sure':
                    features = self.extract_dolum_features(entity_id, lookback_days)
                else:
                    continue
                
                if features:
                    features['entity_id'] = entity_id
                    features['metric_type'] = metric_type
                    features_list.append(features)
            
            if not features_list:
                return None
            
            # DataFrame oluştur
            df = pd.DataFrame(features_list)
            
            logger.info(f"✅ Feature matrix oluşturuldu: {len(df)} entity, {len(df.columns)} feature")
            
            return df
            
        except Exception as e:
            logger.error(f"Feature matrix oluşturma hatası: {str(e)}")
            return None
    
    # Helper methods
    
    def _calculate_trend(self, values):
        """Trend hesapla: 1 (artış), 0 (sabit), -1 (azalış)"""
        if len(values) < 2:
            return 0
        
        first_half = np.mean(values[:len(values)//2])
        second_half = np.mean(values[len(values)//2:])
        
        diff = second_half - first_half
        threshold = np.std(values) * 0.5
        
        if diff > threshold:
            return 1
        elif diff < -threshold:
            return -1
        else:
            return 0
    
    def _calculate_slope(self, timestamps, values):
        """Linear regression slope hesapla"""
        if len(values) < 2:
            return 0
        
        # Timestamp'leri sayıya çevir (saniye)
        x = np.array([(t - timestamps[0]).total_seconds() for t in timestamps])
        y = np.array(values)
        
        # Linear regression
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2 + 1e-6)
        
        return float(slope)
    
    def _calculate_z_score(self, value, values):
        """Z-score hesapla"""
        mean = np.mean(values)
        std = np.std(values)
        
        if std < 1e-6:
            return 0
        
        return float((value - mean) / std)
    
    def _calculate_iqr_score(self, value, values):
        """IQR-based anomaly score"""
        q25 = np.percentile(values, 25)
        q75 = np.percentile(values, 75)
        iqr = q75 - q25
        
        if iqr < 1e-6:
            return 0
        
        # Alt ve üst sınırlar
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr
        
        if value < lower_bound:
            return float((lower_bound - value) / iqr)
        elif value > upper_bound:
            return float((value - upper_bound) / iqr)
        else:
            return 0
    
    def _get_season(self, month):
        """Mevsim belirle"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'


# Kullanım örneği
def extract_features_for_training(metric_type='stok_seviye', lookback_days=30):
    """Model eğitimi için feature'ları çıkar"""
    try:
        from models import db
        from app import app
        
        with app.app_context():
            engineer = FeatureEngineer(db)
            df = engineer.create_feature_matrix(metric_type, lookback_days=lookback_days)
            
            if df is not None:
                logger.info(f"✅ {len(df)} entity için feature'lar çıkarıldı")
                logger.info(f"Feature'lar: {list(df.columns)}")
                return df
            else:
                logger.warning("⚠️  Feature çıkarılamadı")
                return None
                
    except Exception as e:
        logger.error(f"❌ Feature extraction hatası: {str(e)}")
        return None
