"""
Backup'tan Belirli Tabloları Çıkar ve Geri Yükle
Sadece: oteller, katlar, odalar, kullanicilar, urun_gruplari, urunler
"""

import subprocess
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Geri yüklenecek tablolar
TABLES = [
    'oteller',
    'kullanicilar',
    'kullanici_otel',
    'katlar',
    'odalar',
    'urun_gruplari',
    'urunler'
]

def extract_and_restore():
    """Backup'tan tabloları çıkar ve geri yükle"""
    try:
        backup_file = r'D:\minibartakip2cool\backups\backup_20251112_210802_6d6481c2.sql'
        
        # PostgreSQL bağlantı bilgileri
        db_url = os.getenv('DATABASE_URL')
        # postgres://postgres:518518Erkan@localhost:5432/minibar_takip
        
        logger.info("📂 Backup dosyası: " + os.path.basename(backup_file))
        logger.info(f"📋 Yüklenecek tablolar: {', '.join(TABLES)}")
        logger.info("")
        
        # Her tablo için
        for table in TABLES:
            logger.info(f"🔄 {table} tablosu işleniyor...")
            
            # pg_restore ile sadece bu tabloyu geri yükle
            cmd = [
                'pg_restore',
                '--host=localhost',
                '--port=5432',
                '--username=postgres',
                '--dbname=minibar_takip',
                '--data-only',  # Sadece veri
                '--table=' + table,
                '--clean',  # Önce temizle
                '--if-exists',
                backup_file
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = '518518Erkan'
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"   ✓ {table} başarıyla yüklendi")
            else:
                logger.warning(f"   ⚠ {table} yüklenemedi: {result.stderr}")
            
            logger.info("")
        
        logger.info("✅ İşlem tamamlandı!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🏨 OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   BACKUP'TAN TABLO GERİ YÜKLEME")
    print("=" * 60)
    print()
    print(f"📋 Tablolar: {', '.join(TABLES)}")
    print()
    print("⚠️  UYARI: Bu tablolardaki mevcut veriler silinecek!")
    print()
    
    confirm = input("Devam etmek istiyor musun? (EVET yazarak onayla): ")
    
    if confirm.strip().upper() == "EVET":
        print()
        success = extract_and_restore()
        
        if success:
            print()
            print("=" * 60)
            print("✅ İşlem tamamlandı!")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("❌ İşlem başarısız!")
            print("=" * 60)
    else:
        print()
        print("❌ İşlem iptal edildi.")
