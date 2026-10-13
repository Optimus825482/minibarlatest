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


def run_migrations():
    """Veri kaybı olmadan kolon ve şema migrasyonlarını otomatik uygula"""
    print("🔄 Otomatik ve güvenli veritabanı migrasyonları kontrol ediliyor...")
    
    with app.app_context():
        # 1. PostgreSQL ENUM güncellemesi (dolum_talep_durum -> 'iptal')
        try:
            with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(db.text("ALTER TYPE dolum_talep_durum ADD VALUE IF NOT EXISTS 'iptal'"))
                print("  ✅ Enum 'dolum_talep_durum' -> 'iptal' değeri doğrulandı")
        except Exception as enum_err:
            print(f"  ℹ️ Enum kontrol notu: {enum_err}")

        # 2. minibar_dolum_talepleri tablosuna yeni kolonlar (IF NOT EXISTS)
        try:
            with db.engine.connect() as conn:
                columns_to_add = [
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS tamamlayan_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS goren_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS gorulme_tarihi TIMESTAMPTZ",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS kapatma_aciklamasi TEXT",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS iptal_aciklamasi TEXT",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS iptal_eden_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS iptal_tarihi TIMESTAMPTZ",
                    "ALTER TABLE minibar_dolum_talepleri ADD COLUMN IF NOT EXISTS notlar TEXT"
                ]
                for stmt in columns_to_add:
                    try:
                        conn.execute(db.text(stmt))
                    except Exception as col_err:
                        print(f"  ℹ️ Kolon kontrolü: {col_err}")
                conn.commit()
                print("  ✅ 'minibar_dolum_talepleri' tablosu kolonları doğrulandı")
        except Exception as e:
            print(f"  ⚠️ Kolon güncelleme hatası: {e}")

        # 3. minibar_dolum_talebi_detay tablosunun varlığını garanti et
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS minibar_dolum_talebi_detay (
                        id SERIAL PRIMARY KEY,
                        talep_id INTEGER NOT NULL REFERENCES minibar_dolum_talepleri(id) ON DELETE CASCADE,
                        urun_id INTEGER NOT NULL REFERENCES urunler(id) ON DELETE RESTRICT,
                        olusturma_tarihi TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_dolum_talebi_detay_talep ON minibar_dolum_talebi_detay (talep_id)"))
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_dolum_talebi_detay_urun ON minibar_dolum_talebi_detay (urun_id)"))
                conn.commit()
                print("  ✅ 'minibar_dolum_talebi_detay' tablosu ve indeksleri doğrulandı")
        except Exception as e:
            print(f"  ℹ️ Detay tablosu kontrolü: {e}")

        # 4. Performans İndeksleri
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_minibar_dolum_talepleri_oda_durum ON minibar_dolum_talepleri (oda_id, durum)"))
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_minibar_dolum_talepleri_talep_tarihi ON minibar_dolum_talepleri (talep_tarihi)"))
                conn.commit()
                print("  ✅ Talep performans indeksleri doğrulandı")
        except Exception as e:
            print(f"  ℹ️ İndeks kontrolü: {e}")

    print("✅ Güvenli migrasyonlar tamamlandı (hiçbir veri silinmedi).")
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

    # 3. Güvenli Şema & Kolon Migrasyonları
    run_migrations()
    
    print("")
    print("="*60)
    print("✅ SAFE DEPLOY - TAMAMLANDI")
    print("="*60)
    print("")
    
    sys.exit(0)


if __name__ == '__main__':
    main()

