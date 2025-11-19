"""
Satın alma işlemlerine durum ve iptal alanları ekleme
Tarih: 2025-11-19
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from models import db
from sqlalchemy import text

# Flask app oluştur
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def upgrade():
    """Yeni alanları ekle"""
    with app.app_context():
        try:
            # Durum alanı ekle
            db.session.execute(text("""
                ALTER TABLE satin_alma_islemler 
                ADD COLUMN IF NOT EXISTS durum VARCHAR(20) DEFAULT 'aktif' NOT NULL
            """))
            
            # İptal tarihi ekle
            db.session.execute(text("""
                ALTER TABLE satin_alma_islemler 
                ADD COLUMN IF NOT EXISTS iptal_tarihi TIMESTAMP WITH TIME ZONE
            """))
            
            # İptal eden kullanıcı ekle
            db.session.execute(text("""
                ALTER TABLE satin_alma_islemler 
                ADD COLUMN IF NOT EXISTS iptal_eden_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL
            """))
            
            # İptal açıklaması ekle
            db.session.execute(text("""
                ALTER TABLE satin_alma_islemler 
                ADD COLUMN IF NOT EXISTS iptal_aciklama TEXT
            """))
            
            db.session.commit()
            print("✅ Satın alma işlem durum alanları başarıyla eklendi")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")
            raise

def downgrade():
    """Alanları kaldır"""
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE satin_alma_islemler DROP COLUMN IF EXISTS durum"))
            db.session.execute(text("ALTER TABLE satin_alma_islemler DROP COLUMN IF EXISTS iptal_tarihi"))
            db.session.execute(text("ALTER TABLE satin_alma_islemler DROP COLUMN IF EXISTS iptal_eden_id"))
            db.session.execute(text("ALTER TABLE satin_alma_islemler DROP COLUMN IF EXISTS iptal_aciklama"))
            
            db.session.commit()
            print("✅ Satın alma işlem durum alanları başarıyla kaldırıldı")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")
            raise

if __name__ == '__main__':
    print("Satın alma işlem durum alanları migration başlatılıyor...")
    upgrade()
