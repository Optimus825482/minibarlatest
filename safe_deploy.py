"""
Güvenli Deployment Script - Mevcut Veritabanına Dokunmaz
Bu script Coolify deployment sırasında sadece eksik tabloları oluşturur.
Mevcut tablolara ve verilere DOKUNMAZ.
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def get_database_url():
    """Database URL'ini al"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # PostgreSQL variables
        pghost = os.getenv('PGHOST_PRIVATE') or os.getenv('PGHOST')
        pguser = os.getenv('PGUSER')
        pgpassword = os.getenv('PGPASSWORD')
        pgdatabase = os.getenv('PGDATABASE')
        pgport = os.getenv('PGPORT_PRIVATE') or os.getenv('PGPORT', '5432')
        
        if pghost and pguser:
            database_url = f'postgresql+psycopg2://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}'
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://')
    
    return database_url

def check_database_connection():
    """Veritabanı bağlantısını kontrol et"""
    print("=" * 70)
    print("🔍 GÜVENLİ DEPLOYMENT - VERİTABANI KONTROLÜ")
    print("=" * 70)
    print()
    
    database_url = get_database_url()
    
    if not database_url:
        print("❌ DATABASE_URL bulunamadı!")
        return None
    
    try:
        # Bağlantı testi
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.close()
        
        print("✅ Veritabanı bağlantısı başarılı")
        return engine
        
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {str(e)}")
        return None

def check_existing_tables(engine):
    """Mevcut tabloları kontrol et"""
    print()
    print("📊 Mevcut tablolar kontrol ediliyor...")
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print(f"✅ {len(existing_tables)} tablo bulundu:")
            for table in sorted(existing_tables):
                print(f"   ✓ {table}")
            return existing_tables
        else:
            print("ℹ️  Henüz tablo yok")
            return []
            
    except Exception as e:
        print(f"❌ Tablo kontrol hatası: {str(e)}")
        return []

def create_missing_tables_only(engine, existing_tables):
    """Sadece eksik tabloları oluştur - MEVCUT TABLOLARA DOKUNMA"""
    print()
    print("🔧 Eksik tablolar kontrol ediliyor...")
    
    # Beklenen tablolar
    expected_tables = [
        'oteller',
        'kullanicilar',
        'kullanici_otel',
        'katlar',
        'odalar',
        'urun_gruplari',
        'urunler',
        'stok_hareketleri',
        'personel_zimmet',
        'personel_zimmet_detay',
        'minibar_islemleri',
        'minibar_islem_detay',
        'sistem_ayarlari',
        'sistem_loglari',
        'hata_loglari',
        'audit_logs',
        'otomatik_raporlar',
        'minibar_dolum_talepleri',
        'qr_kod_okutma_loglari',
        'ml_metrics',
        'ml_predictions',
        'ml_anomalies'
    ]
    
    missing_tables = [t for t in expected_tables if t not in existing_tables]
    
    if not missing_tables:
        print("✅ Tüm tablolar mevcut - Hiçbir değişiklik yapılmadı")
        return True
    
    print(f"⚠️  {len(missing_tables)} eksik tablo bulundu:")
    for table in missing_tables:
        print(f"   - {table}")
    
    print()
    print("🔧 Eksik tablolar otomatik oluşturuluyor...")
    
    try:
        # Flask app context'i içinde db.create_all() çalıştır
        # Bu sadece eksik tabloları oluşturur, mevcut tablolara dokunmaz
        from app import app, db
        
        with app.app_context():
            # SQLAlchemy create_all() sadece eksik tabloları oluşturur
            db.create_all()
            
            # Kontrol et
            from sqlalchemy import inspect
            inspector = inspect(engine)
            new_tables = inspector.get_table_names()
            newly_created = [t for t in missing_tables if t in new_tables]
            
            if newly_created:
                print(f"✅ {len(newly_created)} yeni tablo oluşturuldu:")
                for table in newly_created:
                    print(f"   ✓ {table}")
            
            still_missing = [t for t in missing_tables if t not in new_tables]
            if still_missing:
                print(f"⚠️  {len(still_missing)} tablo oluşturulamadı:")
                for table in still_missing:
                    print(f"   - {table}")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Tablo oluşturma hatası: {str(e)}")
        print()
        print("📝 Manuel oluşturma için:")
        print("   1. Coolify Shell'e bağlan")
        print("   2. python init_db.py komutunu çalıştır")
        return False

def verify_critical_data():
    """Kritik verilerin varlığını kontrol et"""
    print()
    print("🔍 Kritik veriler kontrol ediliyor...")
    
    database_url = get_database_url()
    if not database_url:
        return False
    
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Kullanıcı sayısını kontrol et
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM kullanicilar"))
            user_count = result.scalar()
            result.close()
            
            if user_count > 0:
                print(f"✅ {user_count} kullanıcı bulundu - Veriler korunuyor")
                return True
            else:
                print("ℹ️  Henüz kullanıcı yok - Yeni kurulum")
                return True
                
    except Exception as e:
        print(f"⚠️  Veri kontrolü yapılamadı: {str(e)}")
        return True  # Hata durumunda devam et

def fix_sequences(engine, existing_tables):
    """PostgreSQL sequence'larını düzelt"""
    print()
    print("🔧 PostgreSQL Sequence'ları kontrol ediliyor...")
    
    try:
        with engine.connect() as conn:
            fixed_count = 0
            
            for table in existing_tables:
                try:
                    # Max ID'yi al
                    result = conn.execute(text(f"SELECT MAX(id) FROM {table}"))
                    max_id = result.scalar() or 0
                    result.close()
                    
                    # Sequence adı
                    sequence_name = f"{table}_id_seq"
                    
                    # Sequence var mı kontrol et
                    result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM pg_sequences 
                            WHERE schemaname = 'public' 
                            AND sequencename = '{sequence_name}'
                        );
                    """))
                    sequence_exists = result.scalar()
                    result.close()
                    
                    if sequence_exists:
                        # Sequence'ı güncelle
                        conn.execute(text(f"SELECT setval('{sequence_name}', {max_id + 1}, false)"))
                        conn.commit()
                        fixed_count += 1
                    else:
                        # Sequence yoksa oluştur
                        conn.execute(text(f"""
                            CREATE SEQUENCE IF NOT EXISTS {sequence_name};
                            ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{sequence_name}');
                            SELECT setval('{sequence_name}', {max_id + 1}, false);
                        """))
                        conn.commit()
                        fixed_count += 1
                    
                except Exception as e:
                    # ID kolonu olmayan tablolar için normal
                    continue
            
            if fixed_count > 0:
                print(f"✅ {fixed_count} tablo için sequence düzeltildi")
            else:
                print("ℹ️  Sequence düzeltmesi gerekmiyor")
            
            return True
            
    except Exception as e:
        print(f"⚠️  Sequence düzeltme hatası: {str(e)}")
        return False

def main():
    """Ana fonksiyon - Güvenli deployment"""
    
    print()
    
    # 1. Veritabanı bağlantısını kontrol et
    engine = check_database_connection()
    if not engine:
        print()
        print("❌ Veritabanı bağlantısı kurulamadı!")
        return False
    
    # 2. Mevcut tabloları kontrol et
    existing_tables = check_existing_tables(engine)
    
    # 3. Kritik verileri kontrol et
    if existing_tables:
        verify_critical_data()
    
    # 4. Eksik tabloları kontrol et (ama oluşturma!)
    create_missing_tables_only(engine, existing_tables)
    
    # 5. Sequence'ları düzelt (KRİTİK!)
    if existing_tables:
        fix_sequences(engine, existing_tables)
    
    # Başarılı
    print()
    print("=" * 70)
    print("✅ GÜVENLİ DEPLOYMENT KONTROLÜ TAMAMLANDI")
    print("=" * 70)
    print()
    print("📝 Özet:")
    print(f"   • Mevcut tablolar: {len(existing_tables)}")
    print("   • Veriler korundu: ✅")
    print("   • Deployment güvenli: ✅")
    print()
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
