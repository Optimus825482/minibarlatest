"""
Migration: Kullanıcı Tema Ayarları Ekleme

Kullanıcıların kendi renk temalarını seçebilmeleri için
kullanicilar tablosuna tema_renk_1 ve tema_renk_2 kolonları eklenir.
"""

import sys
import os

# Proje root dizinini Python path'ine ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv()

from models.base import db
from models.kullanici import Kullanici
from sqlalchemy import text
from config import Config

def run_migration():
    """Migration'ı çalıştır"""
    print("🔄 Tema ayarları migration başlatılıyor...")
    
    try:
        # Flask app context'i olmadan direkt SQLAlchemy kullan
        from sqlalchemy import create_engine
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        with engine.connect() as conn:
            # Kolonların var olup olmadığını kontrol et
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'kullanicilar' 
                AND column_name IN ('tema_renk_1', 'tema_renk_2')
            """))
            
            existing_columns = [row[0] for row in result]
            
            if 'tema_renk_1' in existing_columns and 'tema_renk_2' in existing_columns:
                print("✅ Tema kolonları zaten mevcut!")
                return
            
            # Kolonları ekle
            if 'tema_renk_1' not in existing_columns:
                print("➕ tema_renk_1 kolonu ekleniyor...")
                conn.execute(text("""
                    ALTER TABLE kullanicilar 
                    ADD COLUMN tema_renk_1 VARCHAR(7) DEFAULT '#2563EB'
                """))
                conn.commit()
                print("✅ tema_renk_1 kolonu eklendi!")
            
            if 'tema_renk_2' not in existing_columns:
                print("➕ tema_renk_2 kolonu ekleniyor...")
                conn.execute(text("""
                    ALTER TABLE kullanicilar 
                    ADD COLUMN tema_renk_2 VARCHAR(7) DEFAULT '#0284C7'
                """))
                conn.commit()
                print("✅ tema_renk_2 kolonu eklendi!")
            
            # Mevcut kullanıcılar için default değerleri ayarla
            print("🔄 Mevcut kullanıcılar için default tema ayarlanıyor...")
            conn.execute(text("""
                UPDATE kullanicilar 
                SET tema_renk_1 = '#2563EB', tema_renk_2 = '#0284C7'
                WHERE tema_renk_1 IS NULL OR tema_renk_2 IS NULL
            """))
            conn.commit()
            
            print("✅ Migration başarıyla tamamlandı!")
            print("📊 Eklenen kolonlar:")
            print("   - tema_renk_1 (VARCHAR(7), default: #2563EB)")
            print("   - tema_renk_2 (VARCHAR(7), default: #0284C7)")
            
    except Exception as e:
        print(f"❌ Migration hatası: {str(e)}")
        raise

if __name__ == '__main__':
    run_migration()
