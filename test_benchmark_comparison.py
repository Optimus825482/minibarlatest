"""
Feature Storage Benchmark Comparison
Kaydedilmiş feature'lar vs Yeni hesaplama karşılaştırması
"""

import time
from app import app
from models import db
from utils.ml.feature_engineer import FeatureEngineer
from utils.ml.feature_storage import FeatureStorage
from utils.ml.model_trainer import ModelTrainer
import numpy as np

def benchmark_feature_storage():
    """Feature storage performans karşılaştırması"""
    
    with app.app_context():
        print("="*80)
        print("FEATURE STORAGE PERFORMANS KARŞILAŞTIRMASI")
        print("="*80)
        
        engineer = FeatureEngineer(db)
        storage = FeatureStorage(db)
        
        # Test 1: Feature Extraction (İlk kez - kaydetme ile)
        print("\n" + "="*80)
        print("TEST 1: Feature Extraction + Kaydetme")
        print("="*80)
        
        start = time.time()
        features_1 = engineer.extract_stok_features(1, lookback_days=30, save_to_db=True)
        features_2 = engineer.extract_stok_features(2, lookback_days=30, save_to_db=True)
        features_3 = engineer.extract_stok_features(3, lookback_days=30, save_to_db=True)
        duration_save = time.time() - start
        
        print(f"⏱️  Süre (3 ürün): {duration_save:.3f} saniye")
        print(f"📊 Feature sayısı: {len(features_1) if features_1 else 0}")
        
        # Test 2: Feature Retrieval (Kaydedilmiş)
        print("\n" + "="*80)
        print("TEST 2: Kaydedilmiş Feature'ları Getirme")
        print("="*80)
        
        start = time.time()
        stored_1 = storage.get_latest_features('stok_seviye', 1)
        stored_2 = storage.get_latest_features('stok_seviye', 2)
        stored_3 = storage.get_latest_features('stok_seviye', 3)
        duration_retrieve = time.time() - start
        
        print(f"⏱️  Süre (3 ürün): {duration_retrieve:.3f} saniye")
        print(f"📊 Feature sayısı: {len(stored_1) if stored_1 else 0}")
        
        # Karşılaştırma
        speedup = duration_save / duration_retrieve if duration_retrieve > 0 else 0
        improvement = ((duration_save - duration_retrieve) / duration_save * 100) if duration_save > 0 else 0
        
        print(f"\n🚀 HIZ ARTIŞI: {speedup:.1f}x")
        print(f"📈 İYİLEŞME: %{improvement:.1f}")
        
        # Test 3: Feature Matrix (Yeni hesaplama)
        print("\n" + "="*80)
        print("TEST 3: Feature Matrix - Yeni Hesaplama")
        print("="*80)
        
        start = time.time()
        df_new = engineer.create_feature_matrix('stok_seviye', lookback_days=30)
        duration_matrix_new = time.time() - start
        
        print(f"⏱️  Süre: {duration_matrix_new:.3f} saniye")
        print(f"📊 Shape: {df_new.shape if df_new is not None else 'None'}")
        
        # Test 4: Feature Matrix (Kaydedilmiş)
        print("\n" + "="*80)
        print("TEST 4: Feature Matrix - Kaydedilmiş")
        print("="*80)
        
        start = time.time()
        df_stored = storage.get_feature_matrix('stok_seviye', lookback_days=30)
        duration_matrix_stored = time.time() - start
        
        print(f"⏱️  Süre: {duration_matrix_stored:.3f} saniye")
        print(f"📊 Shape: {df_stored.shape if df_stored is not None else 'None'}")
        
        # Karşılaştırma
        speedup_matrix = duration_matrix_new / duration_matrix_stored if duration_matrix_stored > 0 else 0
        improvement_matrix = ((duration_matrix_new - duration_matrix_stored) / duration_matrix_new * 100) if duration_matrix_new > 0 else 0
        
        print(f"\n🚀 HIZ ARTIŞI: {speedup_matrix:.1f}x")
        print(f"📈 İYİLEŞME: %{improvement_matrix:.1f}")
        
        # Test 5: Model Training Karşılaştırması
        print("\n" + "="*80)
        print("TEST 5: Model Training - Ham Veri")
        print("="*80)
        
        from models import MLMetric
        from datetime import datetime, timezone, timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        metrics = MLMetric.query.filter(
            MLMetric.metric_type == 'stok_seviye',
            MLMetric.timestamp >= cutoff_date
        ).all()
        
        data = np.array([m.metric_value for m in metrics])
        
        trainer = ModelTrainer(db)
        
        start = time.time()
        model_raw = trainer.train_isolation_forest(
            'stok_seviye',
            data,
            use_feature_engineering=False
        )
        duration_raw = time.time() - start
        
        print(f"⏱️  Süre: {duration_raw:.3f} saniye")
        print(f"📊 Accuracy: {model_raw[3] if model_raw[0] else 0:.2%}")
        
        # Test 6: Model Training - Yeni Feature Engineering
        print("\n" + "="*80)
        print("TEST 6: Model Training - Yeni Feature Engineering")
        print("="*80)
        
        start = time.time()
        model_new_fe = trainer.train_isolation_forest(
            'stok_seviye',
            data,
            use_feature_engineering=True,
            use_stored_features=False  # Yeni hesapla
        )
        duration_new_fe = time.time() - start
        
        print(f"⏱️  Süre: {duration_new_fe:.3f} saniye")
        print(f"📊 Accuracy: {model_new_fe[3] if model_new_fe[0] else 0:.2%}")
        print(f"📊 Feature sayısı: {len(model_new_fe[2]) if model_new_fe[2] else 0}")
        
        # Test 7: Model Training - Kaydedilmiş Features
        print("\n" + "="*80)
        print("TEST 7: Model Training - Kaydedilmiş Features")
        print("="*80)
        
        start = time.time()
        model_stored_fe = trainer.train_isolation_forest(
            'stok_seviye',
            data,
            use_feature_engineering=True,
            use_stored_features=True  # Kaydedilmiş kullan
        )
        duration_stored_fe = time.time() - start
        
        print(f"⏱️  Süre: {duration_stored_fe:.3f} saniye")
        print(f"📊 Accuracy: {model_stored_fe[3] if model_stored_fe[0] else 0:.2%}")
        print(f"📊 Feature sayısı: {len(model_stored_fe[2]) if model_stored_fe[2] else 0}")
        
        # Final Karşılaştırma
        print("\n" + "="*80)
        print("ÖZET KARŞILAŞTIRMA")
        print("="*80)
        
        print("\n📊 FEATURE EXTRACTION:")
        print(f"   Yeni hesaplama:     {duration_save:.3f}s")
        print(f"   Kaydedilmiş okuma:  {duration_retrieve:.3f}s")
        print(f"   Hız artışı:         {speedup:.1f}x")
        print(f"   İyileşme:           %{improvement:.1f}")
        
        print("\n📊 FEATURE MATRIX:")
        print(f"   Yeni hesaplama:     {duration_matrix_new:.3f}s")
        print(f"   Kaydedilmiş okuma:  {duration_matrix_stored:.3f}s")
        print(f"   Hız artışı:         {speedup_matrix:.1f}x")
        print(f"   İyileşme:           %{improvement_matrix:.1f}")
        
        print("\n📊 MODEL TRAINING:")
        print(f"   Ham veri:                    {duration_raw:.3f}s")
        print(f"   Yeni feature engineering:    {duration_new_fe:.3f}s")
        print(f"   Kaydedilmiş features:        {duration_stored_fe:.3f}s")
        
        if duration_new_fe > 0:
            speedup_training = duration_new_fe / duration_stored_fe if duration_stored_fe > 0 else 0
            improvement_training = ((duration_new_fe - duration_stored_fe) / duration_new_fe * 100)
            print(f"   Hız artışı (FE vs Stored):   {speedup_training:.1f}x")
            print(f"   İyileşme:                    %{improvement_training:.1f}")
        
        print("\n" + "="*80)
        print("✅ BENCHMARK TAMAMLANDI")
        print("="*80)


if __name__ == '__main__':
    benchmark_feature_storage()
