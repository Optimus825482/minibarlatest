"""
ML Features Table Migration
Feature engineering sonuçlarını saklamak için yeni tablo
"""

from app import app
from models import db
from sqlalchemy import text

def upgrade():
    """Yeni ml_features tablosunu oluştur"""
    
    with app.app_context():
        try:
            # ml_features tablosu oluştur
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS ml_features (
                    id SERIAL PRIMARY KEY,
                    metric_type VARCHAR(50) NOT NULL,
                    entity_id INTEGER NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    
                    -- Statistical Features
                    mean_value FLOAT,
                    std_value FLOAT,
                    min_value FLOAT,
                    max_value FLOAT,
                    median_value FLOAT,
                    q25_value FLOAT,
                    q75_value FLOAT,
                    
                    -- Trend Features
                    trend_slope FLOAT,
                    trend_direction VARCHAR(20),
                    volatility FLOAT,
                    momentum FLOAT,
                    
                    -- Time Features
                    hour_of_day INTEGER,
                    day_of_week INTEGER,
                    is_weekend BOOLEAN,
                    day_of_month INTEGER,
                    
                    -- Domain Specific Features
                    days_since_last_change INTEGER,
                    change_frequency FLOAT,
                    avg_change_magnitude FLOAT,
                    zero_count INTEGER,
                    
                    -- Lag Features
                    lag_1 FLOAT,
                    lag_7 FLOAT,
                    lag_30 FLOAT,
                    
                    -- Rolling Features
                    rolling_mean_7 FLOAT,
                    rolling_std_7 FLOAT,
                    rolling_mean_30 FLOAT,
                    rolling_std_30 FLOAT,
                    
                    -- Ek bilgiler
                    feature_version VARCHAR(20) DEFAULT '1.0',
                    extra_features JSONB,
                    
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            
            # Index'ler oluştur
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ml_features_type_entity 
                ON ml_features(metric_type, entity_id);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ml_features_timestamp 
                ON ml_features(timestamp DESC);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ml_features_entity_time 
                ON ml_features(entity_id, timestamp DESC);
            """))
            
            db.session.commit()
            print("✅ ml_features tablosu başarıyla oluşturuldu!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")
            raise

def downgrade():
    """Tabloyu geri al"""
    with app.app_context():
        try:
            db.session.execute(text("DROP TABLE IF EXISTS ml_features CASCADE;"))
            db.session.commit()
            print("✅ ml_features tablosu silindi")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")
            raise

if __name__ == '__main__':
    print("ML Features tablosu oluşturuluyor...")
    upgrade()
