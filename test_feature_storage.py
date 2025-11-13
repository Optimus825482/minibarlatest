"""
Feature Storage Test Script
"""

from app import app
from models import db, MLFeature, MLMetric
from utils.ml.feature_storage import FeatureStorage
from utils.ml.feature_engineer import FeatureEngineer

def test_feature_storage():
    """Feature storage sistemini test et"""
    
    with app.app_context():
        print("="*60)
        print("FEATURE STORAGE TEST")
        print("="*60)
        
        # 1. Tablo kontrolü
        try:
            count = MLFeature.query.count()
            print(f"\n✅ ml_features tablosu mevcut")
            print(f"   Toplam kayıt: {count}")
        except Exception as e:
            print(f"\n❌ Tablo hatası: {str(e)}")
            return
        
        # 2. Feature Engineering Test
        print("\n" + "-"*60)
        print("Feature Engineering Test")
        print("-"*60)
        
        engineer = FeatureEngineer(db)
        
        # İlk ürün için feature çıkar
        try:
            features = engineer.extract_stok_features(
                urun_id=1,
                lookback_days=30,
                save_to_db=True
            )
            
            if features:
                print(f"✅ Feature extraction başarılı")
                print(f"   Feature sayısı: {len(features)}")
                print(f"   Örnek feature'lar:")
                for key in list(features.keys())[:5]:
                    print(f"     - {key}: {features[key]}")
            else:
                print("⚠️  Yetersiz veri (en az 2 metrik gerekli)")
                
        except Exception as e:
            print(f"❌ Feature extraction hatası: {str(e)}")
        
        # 3. Feature Storage Test
        print("\n" + "-"*60)
        print("Feature Storage Test")
        print("-"*60)
        
        storage = FeatureStorage(db)
        
        # En son feature'ları getir
        try:
            latest = storage.get_latest_features('stok_seviye', entity_id=1)
            
            if latest:
                print(f"✅ Latest features başarılı")
                print(f"   Timestamp: {latest.get('timestamp')}")
                print(f"   Mean: {latest.get('mean')}")
                print(f"   Std: {latest.get('std')}")
                print(f"   Volatility: {latest.get('volatility')}")
            else:
                print("⚠️  Kaydedilmiş feature bulunamadı")
                
        except Exception as e:
            print(f"❌ Feature retrieval hatası: {str(e)}")
        
        # 4. Feature Matrix Test
        print("\n" + "-"*60)
        print("Feature Matrix Test")
        print("-"*60)
        
        try:
            df = storage.get_feature_matrix('stok_seviye', lookback_days=30)
            
            if df is not None:
                print(f"✅ Feature matrix başarılı")
                print(f"   Shape: {df.shape}")
                print(f"   Columns: {list(df.columns)[:5]}...")
            else:
                print("⚠️  Feature matrix oluşturulamadı")
                
        except Exception as e:
            print(f"❌ Feature matrix hatası: {str(e)}")
        
        # 5. İstatistikler
        print("\n" + "-"*60)
        print("Sistem İstatistikleri")
        print("-"*60)
        
        try:
            total_features = MLFeature.query.count()
            total_metrics = MLMetric.query.count()
            
            print(f"📊 Toplam ham metrik: {total_metrics}")
            print(f"📊 Toplam feature: {total_features}")
            
            if total_metrics > 0:
                ratio = (total_features / total_metrics) * 100
                print(f"📊 Feature/Metric oranı: {ratio:.1f}%")
            
        except Exception as e:
            print(f"❌ İstatistik hatası: {str(e)}")
        
        print("\n" + "="*60)
        print("TEST TAMAMLANDI")
        print("="*60)


if __name__ == '__main__':
    test_feature_storage()