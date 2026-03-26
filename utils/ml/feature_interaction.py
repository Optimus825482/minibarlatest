"""
Feature Interaction - Feature'lar arası etkileşim
Polynomial features ve interaction terms
"""

from sklearn.preprocessing import PolynomialFeatures
import logging

logger = logging.getLogger(__name__)


class FeatureInteraction:
    """Feature interaction generator"""
    
    def __init__(self):
        self.poly_transformer = None
        self.interaction_features = []
    
    def create_polynomial_features(self, X, degree=2, interaction_only=False):
        """
        Polynomial features oluştur
        Args:
            X: Feature matrix
            degree: Polinom derecesi
            interaction_only: Sadece interaction terms (x1*x2) mi?
        Returns: Transformed features
        """
        try:
            self.poly_transformer = PolynomialFeatures(
                degree=degree,
                interaction_only=interaction_only,
                include_bias=False
            )
            
            X_poly = self.poly_transformer.fit_transform(X)
            
            logger.info(f"📊 Polynomial features: {X.shape[1]} → {X_poly.shape[1]}")
            
            return X_poly
            
        except Exception as e:
            logger.error(f"Polynomial features hatası: {str(e)}")
            return X
    
    def create_domain_interactions(self, df):
        """
        Domain-specific interaction features
        Stok, tüketim, dolum için özel etkileşimler
        """
        try:
            new_features = {}
            
            # Stok interactions
            if 'mean' in df.columns and 'std' in df.columns:
                new_features['mean_std_ratio'] = df['mean'] / (df['std'] + 1e-6)
            
            if 'current_value' in df.columns and 'mean' in df.columns:
                new_features['current_to_mean_ratio'] = df['current_value'] / (df['mean'] + 1e-6)
            
            if 'distance_to_critical' in df.columns and 'std' in df.columns:
                new_features['critical_distance_normalized'] = df['distance_to_critical'] / (df['std'] + 1e-6)
            
            # Trend interactions
            if 'trend' in df.columns and 'slope' in df.columns:
                new_features['trend_slope_interaction'] = df['trend'] * df['slope']
            
            if 'volatility' in df.columns and 'trend' in df.columns:
                new_features['volatility_trend'] = df['volatility'] * abs(df['trend'])
            
            # Anomaly score interactions
            if 'z_score' in df.columns and 'iqr_score' in df.columns:
                new_features['combined_anomaly_score'] = (abs(df['z_score']) + abs(df['iqr_score'])) / 2
            
            # Tüketim interactions
            if 'weekday_mean' in df.columns and 'weekend_mean' in df.columns:
                new_features['weekday_weekend_diff'] = df['weekday_mean'] - df['weekend_mean']
            
            if 'consumption_per_occupancy' in df.columns and 'mean' in df.columns:
                new_features['efficiency_score'] = df['consumption_per_occupancy'] / (df['mean'] + 1e-6)
            
            # DataFrame'e ekle
            for name, values in new_features.items():
                df[name] = values
                self.interaction_features.append(name)
            
            logger.info(f"✅ {len(new_features)} domain interaction feature eklendi")
            
            return df
            
        except Exception as e:
            logger.error(f"Domain interaction hatası: {str(e)}")
            return df
    
    def create_ratio_features(self, df, feature_pairs):
        """
        Feature çiftleri için ratio features
        Args:
            df: DataFrame
            feature_pairs: [(feature1, feature2), ...] listesi
        """
        try:
            for f1, f2 in feature_pairs:
                if f1 in df.columns and f2 in df.columns:
                    ratio_name = f"{f1}_to_{f2}_ratio"
                    df[ratio_name] = df[f1] / (df[f2] + 1e-6)
                    self.interaction_features.append(ratio_name)
            
            logger.info(f"✅ {len(feature_pairs)} ratio feature eklendi")
            
            return df
            
        except Exception as e:
            logger.error(f"Ratio features hatası: {str(e)}")
            return df
    
    def create_difference_features(self, df, feature_pairs):
        """
        Feature çiftleri için difference features
        """
        try:
            for f1, f2 in feature_pairs:
                if f1 in df.columns and f2 in df.columns:
                    diff_name = f"{f1}_minus_{f2}"
                    df[diff_name] = df[f1] - df[f2]
                    self.interaction_features.append(diff_name)
            
            logger.info(f"✅ {len(feature_pairs)} difference feature eklendi")
            
            return df
            
        except Exception as e:
            logger.error(f"Difference features hatası: {str(e)}")
            return df
    
    def create_product_features(self, df, feature_pairs):
        """
        Feature çiftleri için product features (çarpım)
        """
        try:
            for f1, f2 in feature_pairs:
                if f1 in df.columns and f2 in df.columns:
                    product_name = f"{f1}_times_{f2}"
                    df[product_name] = df[f1] * df[f2]
                    self.interaction_features.append(product_name)
            
            logger.info(f"✅ {len(feature_pairs)} product feature eklendi")
            
            return df
            
        except Exception as e:
            logger.error(f"Product features hatası: {str(e)}")
            return df
    
    def get_interaction_features(self):
        """Oluşturulan interaction feature'ları döndür"""
        return self.interaction_features


# Kullanım örneği
def enhance_features_with_interactions(df):
    """Feature'lara interaction ekle"""
    try:
        interactor = FeatureInteraction()
        
        # Domain-specific interactions
        df = interactor.create_domain_interactions(df)
        
        # Önemli ratio'lar
        important_ratios = [
            ('current_value', 'mean'),
            ('max', 'min'),
            ('q75', 'q25'),
        ]
        df = interactor.create_ratio_features(df, important_ratios)
        
        logger.info(f"✅ Feature interaction tamamlandı: {len(interactor.get_interaction_features())} yeni feature")
        
        return df
        
    except Exception as e:
        logger.error(f"Feature interaction hatası: {str(e)}")
        return df
