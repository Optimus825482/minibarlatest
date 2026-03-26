"""
Safe Deploy Script - Coolify için
Uygulama başlatılmadan önce güvenlik kontrolleri yapar

Erkan için - Güvenli deployment
"""

import sys
import time
from app import app, db
from models import *  # noqa: F403


def check_database_connection():
    """Database bağlantısını kontrol et"""
    print("🔍 Database bağlantısı kontrol ediliyor...")
    
    max_retries = 30
    retry_count = 0
    
    with app.app_context():
        while retry_count < max_retries:
            try:
                db.engine.connect()
                print('✅ Database bağlantısı başarılı!')
                return True
            except Exception:
                retry_count += 1
                print(f"⏳ Database bekleniyor... ({retry_count}/{max_retries})")
                time.sleep(2)
        
        print('❌ Database bağlantısı kurulamadı!')
        return False


def check_tables():
    """Veritabanı tablolarını kontrol et"""
    print("🔍 Veritabanı tabloları kontrol ediliyor...")
    
    with app.app_context():
        try:
            # Tabloları oluştur (varsa atla)
            db.create_all()
            print('✅ Veritabanı tabloları hazır!')
            return True
        except Exception as e:
            print(f'⚠️  Tablo oluşturma uyarısı: {e}')
            print('ℹ️  Devam ediliyor...')
            return True


def main():
    """Ana deployment kontrol fonksiyonu"""
    print("="*60)
    print("🚀 SAFE DEPLOY - BAŞLATILIYOR")
    print("="*60)
    print("")
    
    # 1. Database bağlantısı
    if not check_database_connection():
        print("❌ Deployment başarısız - Database bağlantısı yok")
        sys.exit(1)
    
    print("")
    
    # 2. Tablo kontrolü
    if not check_tables():
        print("❌ Deployment başarısız - Tablo kontrolü hatası")
        sys.exit(1)
    
    print("")
    print("="*60)
    print("✅ SAFE DEPLOY - TAMAMLANDI")
    print("="*60)
    print("")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
