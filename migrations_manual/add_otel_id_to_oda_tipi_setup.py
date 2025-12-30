"""
Migration: oda_tipi_setup tablosuna otel_id sütunu ekleme
Bu migration, setup atamalarını otel bazlı yapar.

Kullanım:
    python migrations_manual/add_otel_id_to_oda_tipi_setup.py upgrade
    python migrations_manual/add_otel_id_to_oda_tipi_setup.py downgrade
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

def get_engine():
    """Veritabanı engine'i oluştur"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    # postgres:// -> postgresql:// dönüşümü (SQLAlchemy 1.4+ için gerekli)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return create_engine(database_url)

def upgrade():
    """otel_id sütununu ekle ve primary key'i güncelle"""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            print("\n🚀 Migration başlatılıyor: oda_tipi_setup tablosuna otel_id ekleme")
            
            # 1. Mevcut verileri yedekle
            print("\n📦 Mevcut veriler yedekleniyor...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS oda_tipi_setup_backup AS 
                SELECT * FROM oda_tipi_setup
            """))
            conn.commit()
            print("  ✅ Yedek tablo oluşturuldu: oda_tipi_setup_backup")
            
            # 2. otel_id sütunu var mı kontrol et
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'oda_tipi_setup' AND column_name = 'otel_id'
            """))
            if result.fetchone():
                print("  ⚠️ otel_id sütunu zaten mevcut, migration atlanıyor")
                return
            
            # 3. Yeni tablo oluştur
            print("\n📝 Yeni tablo yapısı oluşturuluyor...")
            conn.execute(text("""
                CREATE TABLE oda_tipi_setup_new (
                    otel_id INTEGER NOT NULL REFERENCES oteller(id) ON DELETE CASCADE,
                    oda_tipi_id INTEGER NOT NULL REFERENCES oda_tipleri(id) ON DELETE CASCADE,
                    setup_id INTEGER NOT NULL REFERENCES setuplar(id) ON DELETE CASCADE,
                    olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (otel_id, oda_tipi_id, setup_id)
                )
            """))
            conn.commit()
            print("  ✅ Yeni tablo oluşturuldu")
            
            # 4. Mevcut verileri tüm oteller için kopyala (geriye uyumluluk)
            print("\n📋 Mevcut veriler tüm oteller için kopyalanıyor...")
            conn.execute(text("""
                INSERT INTO oda_tipi_setup_new (otel_id, oda_tipi_id, setup_id, olusturma_tarihi)
                SELECT o.id, ots.oda_tipi_id, ots.setup_id, ots.olusturma_tarihi
                FROM oda_tipi_setup ots
                CROSS JOIN oteller o
                WHERE o.aktif = true
                ON CONFLICT DO NOTHING
            """))
            conn.commit()
            print("  ✅ Veriler kopyalandı")
            
            # 5. Eski tabloyu sil ve yenisini yeniden adlandır
            print("\n🔄 Tablolar değiştiriliyor...")
            conn.execute(text("DROP TABLE oda_tipi_setup"))
            conn.execute(text("ALTER TABLE oda_tipi_setup_new RENAME TO oda_tipi_setup"))
            conn.commit()
            print("  ✅ Tablo değiştirildi")
            
            # 6. Index'leri oluştur
            print("\n📊 Index'ler oluşturuluyor...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_oda_tipi_setup_otel 
                ON oda_tipi_setup(otel_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_oda_tipi_setup_oda_tipi 
                ON oda_tipi_setup(oda_tipi_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_oda_tipi_setup_setup 
                ON oda_tipi_setup(setup_id)
            """))
            conn.commit()
            print("  ✅ Index'ler oluşturuldu")
            
            print("\n✅ Migration başarıyla tamamlandı!")
            print("   Artık setup atamaları otel bazlı yapılabilir.")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Migration hatası: {e}")
            raise

def downgrade():
    """otel_id sütununu kaldır ve eski yapıya dön"""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            print("\n🔄 Downgrade başlatılıyor...")
            
            # 1. Yeni tablo oluştur (otel_id olmadan)
            print("\n📝 Eski tablo yapısı oluşturuluyor...")
            conn.execute(text("""
                CREATE TABLE oda_tipi_setup_old (
                    oda_tipi_id INTEGER NOT NULL REFERENCES oda_tipleri(id),
                    setup_id INTEGER NOT NULL REFERENCES setuplar(id),
                    olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (oda_tipi_id, setup_id)
                )
            """))
            conn.commit()
            
            # 2. Verileri kopyala (distinct ile)
            print("\n📋 Veriler kopyalanıyor...")
            conn.execute(text("""
                INSERT INTO oda_tipi_setup_old (oda_tipi_id, setup_id, olusturma_tarihi)
                SELECT DISTINCT oda_tipi_id, setup_id, MIN(olusturma_tarihi)
                FROM oda_tipi_setup
                GROUP BY oda_tipi_id, setup_id
                ON CONFLICT DO NOTHING
            """))
            conn.commit()
            
            # 3. Tabloları değiştir
            print("\n🔄 Tablolar değiştiriliyor...")
            conn.execute(text("DROP TABLE oda_tipi_setup"))
            conn.execute(text("ALTER TABLE oda_tipi_setup_old RENAME TO oda_tipi_setup"))
            conn.commit()
            
            print("\n✅ Downgrade tamamlandı!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Downgrade hatası: {e}")
            raise

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Kullanım: python add_otel_id_to_oda_tipi_setup.py [upgrade|downgrade]")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == 'upgrade':
        upgrade()
    elif action == 'downgrade':
        downgrade()
    else:
        print(f"Bilinmeyen aksiyon: {action}")
        print("Kullanım: python add_otel_id_to_oda_tipi_setup.py [upgrade|downgrade]")
        sys.exit(1)
