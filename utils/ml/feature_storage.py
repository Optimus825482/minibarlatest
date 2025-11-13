"""
Feature Storage Service
Feature'ları veritabanından okuma ve kullanma servisi
"""

from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FeatureStorage:
    """Feature storage ve retrieval servisi"""
    
    def __init__(self, db):
        self.db = db
    
    def get_latest_features(self, metric_type, entity_id):
        """
        Bir entity için en son feature'ları getir
        
        Args:
            metric_type: Metrik tipi
            entity_id: Entity ID
        
        Returns:
            Feature dictionary veya None
        """
        try:
            from models import MLFeature
            
            feature = MLFeature.query.filter_by(
                metric_type=metric_type,
                entity_id=entity_id
            ).order_by(MLFeature.timestamp.desc()).first()
            
            if not feature:
                return None
            
            return self._feature_to_dict(feature)
            
        except Exception as e:
            logger.error(f"Feature getirme hatası: {str(e)}")
            return None
    
    def get_features_in_range(self, metric_type, entity_id, start_date, end_date=None):
        """
        Belirli tarih aralığındaki feature'ları getir
        
        Args:
            metric_type: Metrik tipi
            entity_id: Entity ID
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi (None ise şimdi)
        
        Returns:
            List of feature dictionaries
        """
        try:
            from models import MLFeature
            
            if end_date is None:
                end_date = datetime.now(timezone.utc)
            
            features = MLFeature.query.filter(
                MLFeature.metric_type == metric_type,
                MLFeature.entity_id == entity_id,
                MLFeature.timestamp >= start_date,
                MLFeature.timestamp <= end_date
            ).order_by(MLFeature.timestamp.asc()).all()
            
            return [self._feature_to_dict(f) for f in features]
            
        except Exception as e:
            logger.error(f"Feature range getirme hatası: {str(e)}")
            return []
    
    def get_feature_matrix(self, metric_type, entity_ids=None, lookback_days=30):
        """
        Birden fazla entity için feature matrix oluştur
        
        Args:
            metric_type: Metrik tipi
            entity_ids: Entity ID listesi (None ise hepsi)
            lookback_days: Kaç günlük veri
        
        Returns:
            pandas DataFrame
        """
        try:
            from models import MLFeature
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            query = MLFeature.query.filter(
                MLFeature.metric_type == metric_type,
                MLFeature.timestamp >= cutoff_date
            )
            
            if entity_ids:
                query = query.filter(MLFeature.entity_id.in_(entity_ids))
            
            # Her entity için en son feature'ı al
            features = query.order_by(
                MLFeature.entity_id,
                MLFeature.timestamp.desc()
            ).all()
            
            # Entity başına sadece en son feature
            seen_entities = set()
            unique_features = []
            
            for f in features:
                if f.entity_id not in seen_entities:
                    unique_features.append(f)
                    seen_entities.add(f.entity_id)
            
            if not unique_features:
                return None
            
            # DataFrame'e çevir
            data = []
            for f in unique_features:
                row = self._feature_to_dict(f)
                row['entity_id'] = f.entity_id
                data.append(row)
            
            df = pd.DataFrame(data)
            df.set_index('entity_id', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Feature matrix oluşturma hatası: {str(e)}")
            return None
    
    def get_feature_history(self, metric_type, entity_id, feature_name, lookback_days=30):
        """
        Belirli bir feature'ın zaman serisi geçmişini getir
        
        Args:
            metric_type: Metrik tipi
            entity_id: Entity ID
            feature_name: Feature adı (örn: 'mean_value', 'volatility')
            lookback_days: Kaç günlük veri
        
        Returns:
            pandas Series (timestamp index)
        """
        try:
            from models import MLFeature
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            features = MLFeature.query.filter(
                MLFeature.metric_type == metric_type,
                MLFeature.entity_id == entity_id,
                MLFeature.timestamp >= cutoff_date
            ).order_by(MLFeature.timestamp.asc()).all()
            
            if not features:
                return None
            
            # Feature değerlerini çıkar
            timestamps = [f.timestamp for f in features]
            values = [getattr(f, feature_name, None) for f in features]
            
            # None değerleri filtrele
            valid_data = [(t, v) for t, v in zip(timestamps, values) if v is not None]
            
            if not valid_data:
                return None
            
            timestamps, values = zip(*valid_data)
            
            return pd.Series(values, index=timestamps, name=feature_name)
            
        except Exception as e:
            logger.error(f"Feature history getirme hatası: {str(e)}")
            return None
    
    def _feature_to_dict(self, feature):
        """MLFeature modelini dictionary'ye çevir"""
        feature_dict = {
            # Statistical
            'mean': feature.mean_value,
            'std': feature.std_value,
            'min': feature.min_value,
            'max': feature.max_value,
            'median': feature.median_value,
            'q25': feature.q25_value,
            'q75': feature.q75_value,
            
            # Trend
            'slope': feature.trend_slope,
            'trend': feature.trend_direction,
            'volatility': feature.volatility,
            'momentum': feature.momentum,
            
            # Time
            'hour_of_day': feature.hour_of_day,
            'day_of_week': feature.day_of_week,
            'is_weekend': feature.is_weekend,
            'day_of_month': feature.day_of_month,
            
            # Domain
            'days_since_last_change': feature.days_since_last_change,
            'change_frequency': feature.change_frequency,
            'avg_change_magnitude': feature.avg_change_magnitude,
            'zero_count': feature.zero_count,
            
            # Lag
            'lag_1': feature.lag_1,
            'lag_7': feature.lag_7,
            'lag_30': feature.lag_30,
            
            # Rolling
            'rolling_mean_7': feature.rolling_mean_7,
            'rolling_std_7': feature.rolling_std_7,
            'rolling_mean_30': feature.rolling_mean_30,
            'rolling_std_30': feature.rolling_std_30,
            
            # Metadata
            'timestamp': feature.timestamp,
            'feature_version': feature.feature_version,
        }
        
        # Extra features ekle
        if feature.extra_features:
            feature_dict.update(feature.extra_features)
        
        return feature_dict
    
    def cleanup_old_features(self, days_to_keep=90):
        """
        Eski feature'ları temizle
        
        Args:
            days_to_keep: Kaç günlük veri tutulacak
        
        Returns:
            Silinen kayıt sayısı
        """
        try:
            from models import MLFeature
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            deleted = MLFeature.query.filter(
                MLFeature.timestamp < cutoff_date
            ).delete()
            
            self.db.session.commit()
            
            logger.info(f"✅ {deleted} eski feature kaydı silindi")
            return deleted
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Feature cleanup hatası: {str(e)}")
            return 0


# Kullanım örnekleri
def example_usage():
    """Kullanım örnekleri"""
    from models import db
    from app import app
    
    with app.app_context():
        storage = FeatureStorage(db)
        
        # 1. En son feature'ları getir
        latest = storage.get_latest_features('stok_seviye', urun_id=1)
        print(f"Latest features: {latest}")
        
        # 2. Feature matrix oluştur
        df = storage.get_feature_matrix('stok_seviye', lookback_days=30)
        print(f"Feature matrix shape: {df.shape if df is not None else None}")
        
        # 3. Feature history
        history = storage.get_feature_history('stok_seviye', 1, 'mean', lookback_days=30)
        print(f"Mean history: {len(history) if history is not None else 0} points")
        
        # 4. Cleanup
        deleted = storage.cleanup_old_features(days_to_keep=90)
        print(f"Deleted {deleted} old features")


if __name__ == '__main__':
    example_usage()
