"""
Migration: MLModel tablosuna model_path kolonu ekle ve model_data'yı nullable yap
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import db
from app import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Migration uygula"""
    try:
        with app.app_context():
            logger.info("🔄 Migration başlatılıyor: add_model_path_column")
            
            # 1. model_path kolonu ekle
            logger.info("1️⃣ model_path kolonu ekleniyor...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                ADD COLUMN IF NOT EXISTS model_path VARCHAR(255);
            """))
            
            # 2. model_data'yı nullable yap
            logger.info("2️⃣ model_data kolonu nullable yapılıyor...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                ALTER COLUMN model_data DROP NOT NULL;
            """))
            
            db.session.commit()
            logger.info("✅ Migration başarıyla tamamlandı!")
            
            return True
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Migration hatası: {str(e)}")
        return False


def downgrade():
    """Migration geri al"""
    try:
        with app.app_context():
            logger.info("🔄 Migration geri alınıyor: add_model_path_column")
            
            # 1. model_path kolonunu kaldır
            logger.info("1️⃣ model_path kolonu kaldırılıyor...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                DROP COLUMN IF EXISTS model_path;
            """))
            
            # 2. model_data'yı NOT NULL yap (eğer tüm kayıtlar dolu ise)
            logger.info("2️⃣ model_data kolonu NOT NULL yapılıyor...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                ALTER COLUMN model_data SET NOT NULL;
            """))
            
            db.session.commit()
            logger.info("✅ Migration geri alma başarılı!")
            
            return True
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Migration geri alma hatası: {str(e)}")
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("MLModel Migration - model_path kolonu")
    print("="*60)
    
    response = input("\n❓ Migration'ı uygulamak istiyor musunuz? (evet/hayir): ")
    
    if response.lower() in ['evet', 'e', 'yes', 'y']:
        if upgrade():
            print("\n✅ Migration başarıyla uygulandı!")
        else:
            print("\n❌ Migration başarısız!")
    else:
        print("\n❌ Migration iptal edildi.")
