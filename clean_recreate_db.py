"""
Temiz Veritabanı Yeniden Oluşturma
SQLAlchemy cache'siz, direkt psycopg2 ile
"""

import psycopg2
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def clean_recreate():
    """Veritabanını temizle ve yeniden oluştur"""
    try:
        db_url = os.getenv('DATABASE_URL')
        
        # PostgreSQL bağlantısı
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("🗑️  Veritabanı temizleniyor...")
        
        # Public schema'yı DROP ve yeniden CREATE et
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        cursor.execute("CREATE SCHEMA public;")
        cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        
        logger.info("✅ Veritabanı tamamen temizlendi!")
        
        cursor.close()
        conn.close()
        
        # Şimdi models.py'den tabloları oluştur
        logger.info("🔨 Yeni tablolar oluşturuluyor...")
        
        # Yeni bir Python process'i başlat (cache temiz olsun)
        import subprocess
        
        script = """
from app import app, db
from sqlalchemy import inspect

with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Toplam {len(tables)} tablo oluşturuldu")
    for t in sorted(tables):
        print(f"  ✓ {t}")
"""
        
        result = subprocess.run(['python', '-c', script], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            logger.info("✅ Tüm tablolar başarıyla oluşturuldu!")
            return True
        else:
            logger.error(f"❌ Hata: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🏨 OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   VERİTABANI TEMİZ YENİDEN OLUŞTURMA")
    print("=" * 60)
    print()
    print("⚠️  UYARI: Bu işlem TÜM VERİLERİ SİLECEK!")
    print()
    
    confirm = input("Devam etmek istiyor musun? (EVET yazarak onayla): ")
    
    if confirm.strip().upper() == "EVET":
        print()
        success = clean_recreate()
        
        if success:
            print()
            print("=" * 60)
            print("✅ İşlem tamamlandı!")
            print("   Artık verileri ekleyebilirsin.")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("❌ İşlem başarısız!")
            print("=" * 60)
    else:
        print()
        print("❌ İşlem iptal edildi.")
