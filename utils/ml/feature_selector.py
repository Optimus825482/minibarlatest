"""
Feature Selection - Otomatik Feature Seçimi
En önemli feature'ları seçer, gereksizleri kaldırır
"""

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.ensemble import RandomForestClassifier
import logging

logger = logging.getLogger(__name__)


class FeatureSelector:
    """Otomatik feature selection"""
    
    def __init__(self):
        self.selected_features = None
        self.feature_scores = None
    
    def select_by_variance(self, df, threshold=0.01):
        """
        Düşük varyans feature'ları kaldır
        Args:
            df: Feature DataFrame
            threshold: Minimum varyans eşiği
        Returns: Seçilen feature listesi
        """
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            # Varyans hesapla
            variances = df[numeric_cols].var()
            
            # Düşük varyans feature'ları kaldır
            selected = variances[variances > threshold].index.tolist()
            
            removed = len(numeric_cols) - len(selected)
            logger.info(f"📊 Variance selection: {len(selected)} seçildi, {removed} kaldırıldı")
            
            return selected
            
        except Exception as e:
            logger.error(f"Variance selection hatası: {str(e)}")
            return list(df.columns)
    
    def select_by_correlation(self, df, threshold=0.9):
        """
        Yüksek korelasyonlu feature'ları kaldır
        Args:
            df: Feature DataFrame
            threshold: Korelasyon eşiği (>threshold olanlar kaldırılır)
        Returns: Seçilen feature listesi
        """
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            # Korelasyon matrisi
            corr_matrix = df[numeric_cols].corr().abs()
            
            # Üst üçgen
            upper = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            
            # Yüksek korelasyonlu feature'ları bul
            to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
            
            selected = [col for col in numeric_cols if col not in to_drop]
            
            logger.info(f"📊 Correlation selection: {len(selected)} seçildi, {len(to_drop)} kaldırıldı")
            
            return selected
            
        except Exception as e:
            logger.error(f"Correlation selection hatası: {str(e)}")
            return list(df.columns)
    
    def select_k_best(self, X, y, k=10):
        """
        En iyi K feature'ı seç (supervised)
        Args:
            X: Feature matrix
            y: Target labels
            k: Seçilecek feature sayısı
        Returns: Seçilen feature indeksleri
        """
        try:
            selector = SelectKBest(score_func=f_classif, k=min(k, X.shape[1]))
            selector.fit(X, y)
            
            # Skorlar
            scores = selector.scores_
            selected_indices = selector.get_support(indices=True)
            
            self.feature_scores = scores
            
            logger.info(f"📊 SelectKBest: {len(selected_indices)} feature seçildi")
            
            return selected_indices
            
        except Exception as e:
            logger.error(f"SelectKBest hatası: {str(e)}")
            return np.arange(X.shape[1])
    
    def select_by_importance(self, X, y, threshold=0.01):
        """
        Random Forest feature importance ile seç
        Args:
            X: Feature matrix
            y: Target labels
            threshold: Minimum importance eşiği
        Returns: Seçilen feature indeksleri
        """
        try:
            # Random Forest ile importance hesapla
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            rf.fit(X, y)
            
            importances = rf.feature_importances_
            
            # Threshold üstü feature'lar
            selected_indices = np.where(importances > threshold)[0]
            
            self.feature_scores = importances
            
            logger.info(f"📊 Feature importance: {len(selected_indices)} feature seçildi")
            
            return selected_indices
            
        except Exception as e:
            logger.error(f"Feature importance hatası: {str(e)}")
            return np.arange(X.shape[1])
    
    def auto_select(self, df, method='all'):
        """
        Otomatik feature selection (tüm yöntemler)
        Args:
            df: Feature DataFrame
            method: 'variance', 'correlation', 'all'
        Returns: Seçilen feature listesi
        """
        try:
            selected = list(df.columns)
            
            if method in ['variance', 'all']:
                selected = self.select_by_variance(df)
                df = df[selected]
            
            if method in ['correlation', 'all']:
                selected = self.select_by_correlation(df)
                df = df[selected]
            
            logger.info(f"✅ Auto selection: {len(selected)} feature seçildi")
            self.selected_features = selected
            
            return selected
            
        except Exception as e:
            logger.error(f"Auto selection hatası: {str(e)}")
            return list(df.columns)
    
    def get_feature_ranking(self):
        """Feature ranking'i döndür"""
        if self.feature_scores is None:
            return None
        
        ranking = pd.DataFrame({
            'feature_index': range(len(self.feature_scores)),
            'score': self.feature_scores
        }).sort_values('score', ascending=False)
        
        return ranking


# Kullanım örneği
def select_best_features(df, method='all'):
    """En iyi feature'ları seç"""
    try:
        selector = FeatureSelector()
        selected = selector.auto_select(df, method=method)
        
        logger.info(f"✅ {len(selected)} feature seçildi: {selected[:10]}...")
        
        return selected
        
    except Exception as e:
        logger.error(f"Feature selection hatası: {str(e)}")
        return list(df.columns)
