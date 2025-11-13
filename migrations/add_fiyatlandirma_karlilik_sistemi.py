"""
Fiyatlandırma ve Karlılık Hesaplama Sistemi - Database Migration
Tarih: 2025-11-13
Açıklama: Fiyatlandırma, kampanya, bedelsiz limit, karlılık analizi ve stok yönetimi tablolarını ekler
Gereksinimler: 20.1, 20.2, 20.3
"""

import sys
import os
from pathlib import Path

# Proje kök dizinini Python path'e ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from models import db
from sqlalchemy import text
from dotenv import load_dotenv
from datetime import datetime, timezone

# .env dosyasını yükle
load_dotenv()

# Flask uygulaması oluştur
app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

def upgrade():
    """Fiyatlandırma ve karlılık sistemi tablolarını oluştur"""
    with app.app_context():
        try:
            print("\n" + "="*70)
            print("🚀 FİYATLANDIRMA VE KARLILIK SİSTEMİ MIGRATION BAŞLIYOR")
            print("="*70 + "\n")
            
            # 1. ENUM Tiplerini Oluştur
            print("📋 1. ENUM tipleri oluşturuluyor...")
            create_enum_types()
            print("   ✅ ENUM tipleri oluşturuldu\n")
            
            # 2. Yeni Tabloları Oluştur
            print("📋 2. Yeni tablolar oluşturuluyor...")
            db.create_all()
            print("   ✅ Tüm tablolar oluşturuldu\n")
            
            # 3. MinibarIslemDetay Tablosuna Kolonlar Ekle
            print("📋 3. MinibarIslemDetay tablosuna fiyat kolonları ekleniyor...")
            add_minibar_islem_detay_columns()
            print("   ✅ Fiyat kolonları eklendi\n")
            
            # 4. Foreign Key Constraint'leri Ekle
            print("📋 4. Foreign key constraint'leri ekleniyor...")
            add_foreign_key_constraints()
            print("   ✅ Foreign key constraint'leri eklendi\n")
            
            # 5. Index'leri Oluştur
            print("📋 5. Performans index'leri oluşturuluyor...")
            create_indexes()
            print("   ✅ Index'ler oluşturuldu\n")
            
            # 6. Varsayılan Verileri Ekle
            print("📋 6. Varsayılan veriler ekleniyor...")
            insert_default_data()
            print("   ✅ Varsayılan veriler eklendi\n")
            
            print("="*70)
            print("✅ MİGRATION BAŞARIYLA TAMAMLANDI!")
            print("="*70)
            print("\n📊 Oluşturulan Tablolar (12 adet):")
            print("   • tedarikciler")
            print("   • urun_tedarikci_fiyatlari")
            print("   • urun_fiyat_gecmisi")
            print("   • oda_tipi_satis_fiyatlari")
            print("   • sezon_fiyatlandirma")
            print("   • kampanyalar")
            print("   • bedelsiz_limitler")
            print("   • bedelsiz_kullanim_log")
            print("   • donemsel_kar_analizi")
            print("   • fiyat_guncelleme_kurallari")
            print("   • roi_hesaplamalari")
            print("   • urun_stok")
            print("\n📈 Eklenen Kolonlar (6 adet):")
            print("   • minibar_islem_detay.satis_fiyati")
            print("   • minibar_islem_detay.alis_fiyati")
            print("   • minibar_islem_detay.kar_tutari")
            print("   • minibar_islem_detay.kar_orani")
            print("   • minibar_islem_detay.bedelsiz")
            print("   • minibar_islem_detay.kampanya_id")
            print("\n🔗 Foreign Key Constraint'ler:")
            print("   • minibar_islem_detay → kampanyalar")
            print("\n📊 Index'ler: 15+ performans index'i oluşturuldu")
            print("\n")
            
        except Exception as e:
            print(f"\n❌ HATA: {str(e)}\n")
            raise


def create_enum_types():
    """PostgreSQL ENUM tiplerini oluştur"""
    try:
        # FiyatDegisiklikTipi ENUM
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE fiyatdegisikliktipi AS ENUM ('alis_fiyati', 'satis_fiyati', 'kampanya');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # IndirimTipi ENUM
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE indirimtipi AS ENUM ('yuzde', 'tutar');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # BedelsizLimitTipi ENUM
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE bedelsizlimittipi AS ENUM ('misafir', 'kampanya', 'personel');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # DonemTipi ENUM
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE donemtipi AS ENUM ('gunluk', 'haftalik', 'aylik');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # KuralTipi ENUM
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE kuraltipi AS ENUM ('otomatik_artir', 'otomatik_azalt', 'rakip_fiyat');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"   ⚠️  ENUM oluşturma hatası (zaten var olabilir): {e}")


def add_minibar_islem_detay_columns():
    """MinibarIslemDetay tablosuna fiyat kolonlarını ekle"""
    try:
        # Satis fiyati kolonu
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            ADD COLUMN IF NOT EXISTS satis_fiyati NUMERIC(10, 2)
        """))
        
        # Alis fiyati kolonu
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            ADD COLUMN IF NOT EXISTS alis_fiyati NUMERIC(10, 2)
        """))
        
        # Kar tutari kolonu
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            ADD COLUMN IF NOT EXISTS kar_tutari NUMERIC(10, 2)
        """))
        
        # Kar orani kolonu
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            ADD COLUMN IF NOT EXISTS kar_orani NUMERIC(5, 2)
        """))
        
        # Bedelsiz flag kolonu
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            ADD COLUMN IF NOT EXISTS bedelsiz BOOLEAN DEFAULT FALSE
        """))
        
        # Kampanya ID kolonu (foreign key constraint'i sonra ekleyeceğiz)
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            ADD COLUMN IF NOT EXISTS kampanya_id INTEGER
        """))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"MinibarIslemDetay kolon ekleme hatası: {e}")


def add_foreign_key_constraints():
    """Foreign key constraint'lerini ekle"""
    try:
        # Önce kampanyalar tablosunun id kolonunun PRIMARY KEY olduğunu kontrol et
        result = db.session.execute(text("""
            SELECT constraint_type 
            FROM information_schema.table_constraints 
            WHERE table_name = 'kampanyalar' 
            AND constraint_type = 'PRIMARY KEY'
        """))
        
        has_primary_key = result.fetchone() is not None
        
        if not has_primary_key:
            print("   ⚠️  kampanyalar tablosunda PRIMARY KEY bulunamadı, ekleniyor...")
            # PRIMARY KEY ekle
            db.session.execute(text("""
                ALTER TABLE kampanyalar 
                ADD PRIMARY KEY (id)
            """))
            db.session.commit()
            print("   ✓ PRIMARY KEY eklendi")
        
        # Kampanya foreign key constraint'i ekle
        db.session.execute(text("""
            DO $$ BEGIN
                ALTER TABLE minibar_islem_detay 
                ADD CONSTRAINT fk_minibar_islem_detay_kampanya 
                FOREIGN KEY (kampanya_id) REFERENCES kampanyalar(id) ON DELETE SET NULL;
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"   ⚠️  Foreign key constraint eklenemedi: {e}")
        print("   ℹ️  Bu normal olabilir, manuel kontrol edin.")


def create_indexes():
    """Performans için index'leri oluştur"""
    try:
        indexes = [
            # Tedarikci indexes
            "CREATE INDEX IF NOT EXISTS idx_tedarikci_aktif ON tedarikciler(aktif)",
            
            # UrunTedarikciFiyat indexes
            "CREATE INDEX IF NOT EXISTS idx_urun_tedarikci_aktif ON urun_tedarikci_fiyatlari(urun_id, tedarikci_id, aktif)",
            "CREATE INDEX IF NOT EXISTS idx_urun_fiyat_tarih ON urun_tedarikci_fiyatlari(urun_id, baslangic_tarihi, bitis_tarihi)",
            
            # UrunFiyatGecmisi indexes
            "CREATE INDEX IF NOT EXISTS idx_fiyat_gecmis_urun_tarih ON urun_fiyat_gecmisi(urun_id, degisiklik_tarihi)",
            
            # OdaTipiSatisFiyati indexes
            "CREATE INDEX IF NOT EXISTS idx_oda_tipi_urun_aktif ON oda_tipi_satis_fiyatlari(oda_tipi, urun_id, aktif)",
            
            # SezonFiyatlandirma indexes
            "CREATE INDEX IF NOT EXISTS idx_sezon_tarih_aktif ON sezon_fiyatlandirma(baslangic_tarihi, bitis_tarihi, aktif)",
            
            # Kampanya indexes
            "CREATE INDEX IF NOT EXISTS idx_kampanya_aktif_tarih ON kampanyalar(aktif, baslangic_tarihi, bitis_tarihi)",
            
            # BedelsizLimit indexes
            "CREATE INDEX IF NOT EXISTS idx_bedelsiz_oda_aktif ON bedelsiz_limitler(oda_id, aktif)",
            
            # BedelsizKullanimLog indexes
            "CREATE INDEX IF NOT EXISTS idx_bedelsiz_log_tarih ON bedelsiz_kullanim_log(kullanilma_tarihi)",
            
            # DonemselKarAnalizi indexes
            "CREATE INDEX IF NOT EXISTS idx_kar_analiz_otel_donem ON donemsel_kar_analizi(otel_id, donem_tipi, baslangic_tarihi)",
            
            # FiyatGuncellemeKurali indexes
            "CREATE INDEX IF NOT EXISTS idx_fiyat_kural_aktif ON fiyat_guncelleme_kurallari(aktif)",
            
            # UrunStok indexes
            "CREATE INDEX IF NOT EXISTS idx_urun_stok_otel ON urun_stok(otel_id, urun_id)",
            "CREATE INDEX IF NOT EXISTS idx_urun_stok_kritik ON urun_stok(urun_id) WHERE mevcut_stok <= kritik_stok_seviyesi",
            
            # MinibarIslemDetay yeni kolonlar için indexes
            "CREATE INDEX IF NOT EXISTS idx_minibar_detay_kampanya ON minibar_islem_detay(kampanya_id) WHERE kampanya_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_minibar_detay_bedelsiz ON minibar_islem_detay(bedelsiz) WHERE bedelsiz = TRUE",
        ]
        
        for index_sql in indexes:
            db.session.execute(text(index_sql))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Index oluşturma hatası: {e}")


def insert_default_data():
    """Varsayılan verileri ekle"""
    try:
        # Varsayılan tedarikçi oluştur
        db.session.execute(text("""
            INSERT INTO tedarikciler (tedarikci_adi, iletisim_bilgileri, aktif, olusturma_tarihi)
            SELECT 'Varsayılan Tedarikçi', 
                   '{"telefon": "", "email": "", "adres": ""}'::jsonb,
                   TRUE,
                   NOW()
            WHERE NOT EXISTS (SELECT 1 FROM tedarikciler WHERE tedarikci_adi = 'Varsayılan Tedarikçi')
        """))
        
        db.session.commit()
        print("   ✓ Varsayılan tedarikçi oluşturuldu")
        
    except Exception as e:
        db.session.rollback()
        print(f"   ⚠️  Varsayılan veri ekleme hatası: {e}")


def downgrade():
    """Fiyatlandırma ve karlılık sistemi tablolarını sil (DİKKATLİ KULLAN!)"""
    with app.app_context():
        try:
            print("\n" + "="*70)
            print("⚠️  FİYATLANDIRMA VE KARLILIK SİSTEMİ ROLLBACK BAŞLIYOR")
            print("="*70 + "\n")
            
            # 1. Foreign key constraint'leri kaldır
            print("📋 1. Foreign key constraint'leri kaldırılıyor...")
            remove_foreign_key_constraints()
            print("   ✅ Foreign key constraint'leri kaldırıldı\n")
            
            # 2. MinibarIslemDetay kolonlarını kaldır
            print("📋 2. MinibarIslemDetay kolonları kaldırılıyor...")
            remove_minibar_islem_detay_columns()
            print("   ✅ Kolonlar kaldırıldı\n")
            
            # 3. Tabloları sil (foreign key sırasına dikkat)
            print("📋 3. Tablolar siliniyor...")
            drop_tables()
            print("   ✅ Tablolar silindi\n")
            
            # 4. ENUM tiplerini sil
            print("📋 4. ENUM tipleri siliniyor...")
            drop_enum_types()
            print("   ✅ ENUM tipleri silindi\n")
            
            print("="*70)
            print("✅ ROLLBACK BAŞARIYLA TAMAMLANDI!")
            print("="*70 + "\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ROLLBACK HATASI: {str(e)}\n")
            raise


def remove_foreign_key_constraints():
    """Foreign key constraint'lerini kaldır"""
    try:
        # Kampanya foreign key constraint'i kaldır
        db.session.execute(text("""
            ALTER TABLE minibar_islem_detay 
            DROP CONSTRAINT IF EXISTS fk_minibar_islem_detay_kampanya
        """))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Foreign key constraint kaldırma hatası: {e}")


def remove_minibar_islem_detay_columns():
    """MinibarIslemDetay tablosundan fiyat kolonlarını kaldır"""
    try:
        # Kolonları kaldır
        columns = ['kampanya_id', 'bedelsiz', 'kar_orani', 'kar_tutari', 'alis_fiyati', 'satis_fiyati']
        for column in columns:
            db.session.execute(text(f"""
                ALTER TABLE minibar_islem_detay 
                DROP COLUMN IF EXISTS {column}
            """))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"MinibarIslemDetay kolon kaldırma hatası: {e}")


def drop_tables():
    """Tabloları sil (foreign key sırasına göre)"""
    try:
        tables = [
            'bedelsiz_kullanim_log',
            'bedelsiz_limitler',
            'roi_hesaplamalari',
            'fiyat_guncelleme_kurallari',
            'donemsel_kar_analizi',
            'urun_stok',
            'sezon_fiyatlandirma',
            'oda_tipi_satis_fiyatlari',
            'urun_fiyat_gecmisi',
            'urun_tedarikci_fiyatlari',
            'kampanyalar',
            'tedarikciler',
        ]
        
        for table in tables:
            db.session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            print(f"   ✓ {table} tablosu silindi")
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Tablo silme hatası: {e}")


def drop_enum_types():
    """ENUM tiplerini sil"""
    try:
        enum_types = [
            'kuraltipi',
            'donemtipi',
            'bedelsizlimittipi',
            'indirimtipi',
            'fiyatdegisikliktipi',
        ]
        
        for enum_type in enum_types:
            db.session.execute(text(f"DROP TYPE IF EXISTS {enum_type} CASCADE"))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"ENUM silme hatası: {e}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        print("\n⚠️  UYARI: TÜM FİYATLANDIRMA VE KARLILIK VERİLERİ SİLİNECEK!")
        print("Bu işlem geri alınamaz!\n")
        confirm = input("Devam etmek istediğinize emin misiniz? (yes/no): ")
        if confirm.lower() == 'yes':
            downgrade()
        else:
            print("\n❌ İşlem iptal edildi.\n")
    else:
        upgrade()
