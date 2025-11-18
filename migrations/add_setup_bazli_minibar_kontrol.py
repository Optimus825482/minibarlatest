"""
Migration: Setup Bazlı Minibar Kontrol Sistemi
Tarih: 2025-01-17
Açıklama: Setup bazlı minibar kontrol için gerekli veritabanı değişiklikleri
- Yeni enum değerleri: setup_kontrol, ekstra_ekleme, ekstra_tuketim
- Yeni kolon: minibar_islem_detay.ekstra_miktar
- Performans index'leri
"""

import sys
import os

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def upgrade():
    """Migration'ı uygula"""
    with app.app_context():
        try:
            print("🔄 Setup Bazlı Minibar Kontrol Migration başlatılıyor...")
            
            with db.engine.connect() as conn:
                # 1. Yeni enum değerlerini ekle
                print("\n📝 Yeni enum değerleri ekleniyor...")
                
                conn.execute(text("""
                    ALTER TYPE minibar_islem_tipi ADD VALUE IF NOT EXISTS 'setup_kontrol'
                """))
                conn.commit()
                print("  ✅ setup_kontrol eklendi")
                
                conn.execute(text("""
                    ALTER TYPE minibar_islem_tipi ADD VALUE IF NOT EXISTS 'ekstra_ekleme'
                """))
                conn.commit()
                print("  ✅ ekstra_ekleme eklendi")
                
                conn.execute(text("""
                    ALTER TYPE minibar_islem_tipi ADD VALUE IF NOT EXISTS 'ekstra_tuketim'
                """))
                conn.commit()
                print("  ✅ ekstra_tuketim eklendi")
                
                # 2. ekstra_miktar kolonunu ekle
                print("\n📝 minibar_islem_detay tablosuna ekstra_miktar kolonu ekleniyor...")
                
                conn.execute(text("""
                    ALTER TABLE minibar_islem_detay 
                    ADD COLUMN IF NOT EXISTS ekstra_miktar INTEGER DEFAULT 0
                """))
                conn.commit()
                print("  ✅ ekstra_miktar kolonu eklendi")
                
                # 3. Performans index'lerini oluştur
                print("\n📝 Performans index'leri oluşturuluyor...")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_minibar_islem_oda_tarih 
                    ON minibar_islemleri(oda_id, islem_tarihi)
                """))
                conn.commit()
                print("  ✅ idx_minibar_islem_oda_tarih oluşturuldu")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_minibar_islem_personel_tarih 
                    ON minibar_islemleri(personel_id, islem_tarihi)
                """))
                conn.commit()
                print("  ✅ idx_minibar_islem_personel_tarih oluşturuldu")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_minibar_detay_urun 
                    ON minibar_islem_detay(urun_id)
                """))
                conn.commit()
                print("  ✅ idx_minibar_detay_urun oluşturuldu")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_setup_icerik_setup 
                    ON setup_icerik(setup_id)
                """))
                conn.commit()
                print("  ✅ idx_setup_icerik_setup oluşturuldu")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_oda_tipi_setup_oda_tipi 
                    ON oda_tipi_setup(oda_tipi_id)
                """))
                conn.commit()
                print("  ✅ idx_oda_tipi_setup_oda_tipi oluşturuldu")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_oda_tipi_setup_setup 
                    ON oda_tipi_setup(setup_id)
                """))
                conn.commit()
                print("  ✅ idx_oda_tipi_setup_setup oluşturuldu")
            
            print("\n✅ Migration başarıyla tamamlandı!")
            print("\n📊 Özet:")
            print("  - 3 yeni enum değeri eklendi")
            print("  - 1 yeni kolon eklendi (ekstra_miktar)")
            print("  - 6 performans index'i oluşturuldu")
            return True
            
        except Exception as e:
            print(f"\n❌ Migration hatası: {str(e)}")
            print("⚠️  Rollback yapılıyor...")
            db.session.rollback()
            return False

def downgrade():
    """Migration'ı geri al"""
    with app.app_context():
        try:
            print("🔄 Rollback başlatılıyor...")
            
            with db.engine.connect() as conn:
                # Index'leri sil
                print("\n📝 Index'ler siliniyor...")
                
                conn.execute(text("DROP INDEX IF EXISTS idx_oda_tipi_setup_setup"))
                conn.commit()
                print("  ✅ idx_oda_tipi_setup_setup silindi")
                
                conn.execute(text("DROP INDEX IF EXISTS idx_oda_tipi_setup_oda_tipi"))
                conn.commit()
                print("  ✅ idx_oda_tipi_setup_oda_tipi silindi")
                
                conn.execute(text("DROP INDEX IF EXISTS idx_setup_icerik_setup"))
                conn.commit()
                print("  ✅ idx_setup_icerik_setup silindi")
                
                conn.execute(text("DROP INDEX IF EXISTS idx_minibar_detay_urun"))
                conn.commit()
                print("  ✅ idx_minibar_detay_urun silindi")
                
                conn.execute(text("DROP INDEX IF EXISTS idx_minibar_islem_personel_tarih"))
                conn.commit()
                print("  ✅ idx_minibar_islem_personel_tarih silindi")
                
                conn.execute(text("DROP INDEX IF EXISTS idx_minibar_islem_oda_tarih"))
                conn.commit()
                print("  ✅ idx_minibar_islem_oda_tarih silindi")
                
                # Kolonu sil
                print("\n📝 ekstra_miktar kolonu siliniyor...")
                conn.execute(text("ALTER TABLE minibar_islem_detay DROP COLUMN IF EXISTS ekstra_miktar"))
                conn.commit()
                print("  ✅ ekstra_miktar silindi")
                
                # NOT: Enum değerleri PostgreSQL'de kolayca silinemez
                # Eğer gerçekten geri almak gerekirse enum tipini yeniden oluşturmak gerekir
                print("\n⚠️  NOT: Enum değerleri (setup_kontrol, ekstra_ekleme, ekstra_tuketim)")
                print("    PostgreSQL'de kolayca silinemez. Gerekirse manuel müdahale gerekir.")
            
            print("\n✅ Rollback başarıyla tamamlandı!")
            return True
            
        except Exception as e:
            print(f"\n❌ Rollback hatası: {str(e)}")
            return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
