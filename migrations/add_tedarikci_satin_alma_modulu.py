"""
Tedarikçi ve Satın Alma Modülü Migration Script

Bu script aşağıdaki tabloları oluşturur:
- satin_alma_siparisleri: Satın alma siparişleri
- satin_alma_siparis_detaylari: Sipariş detayları
- tedarikci_performans: Tedarikçi performans metrikleri
- tedarikci_iletisim: Tedarikçi iletişim kayıtları
- tedarikci_dokumanlar: Tedarikçi belge yönetimi

Kullanım:
    python migrations/add_tedarikci_satin_alma_modulu.py
"""

import sys
import os

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect
import sys

def table_exists(table_name):
    """Tablo var mı kontrol et"""
    try:
        inspector = inspect(db.engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        print(f"❌ Tablo kontrol hatası: {str(e)}")
        return False

def create_enum_types():
    """PostgreSQL ENUM tiplerini oluştur"""
    try:
        with db.engine.connect() as conn:
            # SiparisDurum enum'ı
            if not conn.execute(text(
                "SELECT 1 FROM pg_type WHERE typname = 'siparisdurum'"
            )).fetchone():
                conn.execute(text("""
                    CREATE TYPE siparisdurum AS ENUM (
                        'beklemede', 
                        'onaylandi', 
                        'teslim_alindi', 
                        'kismi_teslim', 
                        'tamamlandi', 
                        'iptal'
                    )
                """))
                conn.commit()
                print("✅ SiparisDurum enum tipi oluşturuldu")
            else:
                print("ℹ️  SiparisDurum enum tipi zaten mevcut")

            # DokumanTipi enum'ı
            if not conn.execute(text(
                "SELECT 1 FROM pg_type WHERE typname = 'dokumantipi'"
            )).fetchone():
                conn.execute(text("""
                    CREATE TYPE dokumantipi AS ENUM (
                        'fatura', 
                        'irsaliye', 
                        'sozlesme', 
                        'diger'
                    )
                """))
                conn.commit()
                print("✅ DokumanTipi enum tipi oluşturuldu")
            else:
                print("ℹ️  DokumanTipi enum tipi zaten mevcut")

    except Exception as e:
        print(f"⚠️  ENUM tipleri oluşturulurken hata (devam ediliyor): {str(e)}")

def run_migration():
    """Migration'ı çalıştır"""
    print("=" * 60)
    print("TEDARİKÇİ VE SATIN ALMA MODÜLÜ MIGRATION")
    print("=" * 60)
    
    try:
        with app.app_context():
            # 1. ENUM tiplerini oluştur
            print("\n📋 ENUM tipleri oluşturuluyor...")
            create_enum_types()
            
            # 2. Tabloları kontrol et
            print("\n📋 Mevcut tablolar kontrol ediliyor...")
            tables_to_create = []
            
            if not table_exists('satin_alma_siparisleri'):
                tables_to_create.append('satin_alma_siparisleri')
            else:
                print("ℹ️  satin_alma_siparisleri tablosu zaten mevcut")
            
            if not table_exists('satin_alma_siparis_detaylari'):
                tables_to_create.append('satin_alma_siparis_detaylari')
            else:
                print("ℹ️  satin_alma_siparis_detaylari tablosu zaten mevcut")
            
            if not table_exists('tedarikci_performans'):
                tables_to_create.append('tedarikci_performans')
            else:
                print("ℹ️  tedarikci_performans tablosu zaten mevcut")
            
            if not table_exists('tedarikci_iletisim'):
                tables_to_create.append('tedarikci_iletisim')
            else:
                print("ℹ️  tedarikci_iletisim tablosu zaten mevcut")
            
            if not table_exists('tedarikci_dokumanlar'):
                tables_to_create.append('tedarikci_dokumanlar')
            else:
                print("ℹ️  tedarikci_dokumanlar tablosu zaten mevcut")
            
            # 3. Yeni tabloları oluştur
            if tables_to_create:
                print(f"\n🔨 {len(tables_to_create)} yeni tablo oluşturuluyor...")
                
                # Metadata'dan sadece yeni tabloları oluştur
                metadata = db.metadata
                tables = [metadata.tables[table_name] for table_name in tables_to_create if table_name in metadata.tables]
                
                if tables:
                    for table in tables:
                        table.create(db.engine, checkfirst=True)
                        print(f"✅ {table.name} tablosu oluşturuldu")
                else:
                    # Alternatif: Tüm tabloları oluştur (checkfirst=True ile)
                    db.create_all()
                    print("✅ Tüm tablolar oluşturuldu")
                
                print("\n✅ Migration başarıyla tamamlandı!")
                print("\n📊 Oluşturulan tablolar:")
                for table_name in tables_to_create:
                    print(f"   - {table_name}")
            else:
                print("\n✅ Tüm tablolar zaten mevcut, yeni tablo oluşturulmadı")
            
            # 4. Tablo yapılarını doğrula
            print("\n🔍 Tablo yapıları doğrulanıyor...")
            inspector = inspect(db.engine)
            
            for table_name in ['satin_alma_siparisleri', 'satin_alma_siparis_detaylari', 
                              'tedarikci_performans', 'tedarikci_iletisim', 'tedarikci_dokumanlar']:
                if table_exists(table_name):
                    columns = inspector.get_columns(table_name)
                    indexes = inspector.get_indexes(table_name)
                    print(f"\n✅ {table_name}:")
                    print(f"   - Kolon sayısı: {len(columns)}")
                    print(f"   - İndeks sayısı: {len(indexes)}")
            
            print("\n" + "=" * 60)
            print("✅ MİGRATİON BAŞARIYLA TAMAMLANDI!")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Migration hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
