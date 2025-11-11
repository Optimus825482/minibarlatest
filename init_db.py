"""
Veritabanı ve Tabloları Otomatik Oluşturma Script'i
Bu script sistem ilk çalıştırıldığında veritabanını ve tabloları oluşturur.
"""

import pymysql
from sqlalchemy import create_engine, inspect
from app import app, db
from models import *
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def create_database():
    """MySQL veritabanını oluştur"""
    
    # Railway veya production ortamında çalıştırma - veritabanı zaten var
    database_url = os.getenv('DATABASE_URL')
    mysqlhost = os.getenv('MYSQLHOST')
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    
    if database_url or mysqlhost or railway_env:
        print("=" * 60)
        print("PRODUCTION/RAILWAY DEPLOYMENT - DATABASE SETUP")
        print("=" * 60)
        print("✅ Production MySQL detected (DATABASE_URL or MYSQLHOST found)")
        print("ℹ️  Database already exists, skipping database creation")
        print("📊 Proceeding to table creation...")
        print()
        return True
    
    # Local development için MySQL'e bağlan ve veritabanı oluştur
    mysql_host = os.getenv('DB_HOST', 'localhost')
    mysql_user = os.getenv('DB_USER', 'root')
    mysql_password = os.getenv('DB_PASSWORD', '')
    mysql_db = os.getenv('DB_NAME', 'minibar_takip')
    
    print("=" * 60)
    print("OTEL MİNİBAR TAKİP SİSTEMİ - VERİTABANI KURULUM")
    print("=" * 60)
    print()
    
    try:
        # MySQL'e bağlan (veritabanı olmadan)
        print(f"📡 MySQL sunucusuna bağlanılıyor... ({mysql_host})")
        connection = pymysql.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        cursor = connection.cursor()
        
        # Veritabanını oluştur
        print(f"🗄️  Veritabanı kontrol ediliyor: {mysql_db}")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {mysql_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Veritabanı hazır: {mysql_db}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"❌ MySQL Hatası: {e}")
        print()
        print("🔧 Lütfen kontrol edin:")
        print("   - MySQL servisi çalışıyor mu?")
        print("   - Kullanıcı adı ve şifre doğru mu?")
        print("   - .env dosyası mevcut mu?")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen Hata: {e}")
        return False

def create_tables():
    """SQLAlchemy tablolarını oluştur - GÜVENLİ MOD: Sadece eksik tabloları oluştur"""
    
    print()
    print("📊 Tablolar kontrol ediliyor...")
    
    try:
        with app.app_context():
            # Mevcut tabloları kontrol et
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if existing_tables:
                print(f"ℹ️  Mevcut tablolar bulundu: {len(existing_tables)} tablo")
                for table in sorted(existing_tables):
                    print(f"   ✓ {table}")
                
                # Beklenen tablolar
                expected_tables = [
                    'oteller', 'kullanicilar', 'kullanici_otel', 'katlar', 'odalar',
                    'urun_gruplari', 'urunler', 'stok_hareketleri',
                    'personel_zimmet', 'personel_zimmet_detay',
                    'minibar_islemleri', 'minibar_islem_detay',
                    'sistem_ayarlari', 'sistem_loglari', 'hata_loglari',
                    'audit_logs', 'otomatik_raporlar',
                    'minibar_dolum_talepleri', 'qr_kod_okutma_loglari',
                    'ml_metrics', 'ml_predictions', 'ml_anomalies'
                ]
                
                missing_tables = [t for t in expected_tables if t not in existing_tables]
                
                if missing_tables:
                    print(f"⚠️  {len(missing_tables)} eksik tablo bulundu:")
                    for table in missing_tables:
                        print(f"   - {table}")
                    print()
                    print("🔧 Sadece eksik tablolar oluşturuluyor...")
                    
                    # Sadece eksik tabloları oluştur
                    db.create_all()
                    
                    # Kontrol et
                    inspector = inspect(db.engine)
                    new_tables = inspector.get_table_names()
                    newly_created = [t for t in new_tables if t not in existing_tables]
                    
                    if newly_created:
                        print(f"✅ {len(newly_created)} yeni tablo oluşturuldu:")
                        for table in sorted(newly_created):
                            print(f"   ✓ {table}")
                else:
                    print("✅ Tüm tablolar mevcut - Hiçbir değişiklik yapılmadı")
                    print("🔒 Mevcut veriler korundu")
            else:
                print("ℹ️  Henüz tablo yok, yeni tablolar oluşturuluyor...")
                
                # Tüm tabloları oluştur (ilk kurulum)
                db.create_all()
                
                # Oluşturulan tabloları kontrol et
                inspector = inspect(db.engine)
                all_tables = inspector.get_table_names()
                
                print()
                print(f"✅ Toplam {len(all_tables)} tablo oluşturuldu:")
                for table in sorted(all_tables):
                    print(f"   ✓ {table}")
            
            return True
            
    except Exception as e:
        # Index zaten var hatası görmezden gel
        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
            print(f"ℹ️  Index/constraint zaten mevcut, devam ediliyor...")
            return True
        print(f"❌ Tablo oluşturma hatası: {e}")
        return False

def run_migrations():
    """Eksik kolonları ekle (Railway için migration)"""
    
    print()
    print("🔄 Migration kontrol ediliyor...")
    
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            
            # odalar tablosundaki kolonları kontrol et
            odalar_columns = [col['name'] for col in inspector.get_columns('odalar')]
            
            migrations_needed = []
            
            # QR kod kolonları eksik mi?
            qr_columns = ['qr_kod_token', 'qr_kod_gorsel', 'qr_kod_olusturma_tarihi', 'misafir_mesaji']
            missing_qr_columns = [col for col in qr_columns if col not in odalar_columns]
            
            if missing_qr_columns:
                migrations_needed.append(('odalar', missing_qr_columns))
            
            # personel_zimmet_detay tablosundaki kolonları kontrol et
            zimmet_columns = [col['name'] for col in inspector.get_columns('personel_zimmet_detay')]
            
            if 'kritik_stok_seviyesi' not in zimmet_columns:
                migrations_needed.append(('personel_zimmet_detay', ['kritik_stok_seviyesi']))
            
            if not migrations_needed:
                print("✅ Tüm kolonlar mevcut, migration gerekmiyor")
                return True
            
            # Migration çalıştır
            print(f"⚠️  {len(migrations_needed)} tabloda eksik kolon bulundu")
            
            for table_name, missing_cols in migrations_needed:
                print(f"📝 {table_name} tablosu güncelleniyor...")
                
                if table_name == 'odalar':
                    # QR kod kolonlarını ekle
                    if 'qr_kod_token' in missing_cols:
                        db.engine.execute("ALTER TABLE odalar ADD COLUMN qr_kod_token VARCHAR(64) NULL")
                        print("   ✓ qr_kod_token eklendi")
                    
                    if 'qr_kod_gorsel' in missing_cols:
                        db.engine.execute("ALTER TABLE odalar ADD COLUMN qr_kod_gorsel TEXT NULL")
                        print("   ✓ qr_kod_gorsel eklendi")
                    
                    if 'qr_kod_olusturma_tarihi' in missing_cols:
                        db.engine.execute("ALTER TABLE odalar ADD COLUMN qr_kod_olusturma_tarihi DATETIME NULL")
                        print("   ✓ qr_kod_olusturma_tarihi eklendi")
                    
                    if 'misafir_mesaji' in missing_cols:
                        db.engine.execute("ALTER TABLE odalar ADD COLUMN misafir_mesaji VARCHAR(500) NULL")
                        print("   ✓ misafir_mesaji eklendi")
                
                elif table_name == 'personel_zimmet_detay':
                    # Kritik stok seviyesi kolonunu ekle
                    if 'kritik_stok_seviyesi' in missing_cols:
                        db.engine.execute("ALTER TABLE personel_zimmet_detay ADD COLUMN kritik_stok_seviyesi INTEGER NULL DEFAULT 0")
                        print("   ✓ kritik_stok_seviyesi eklendi")
            
            print("✅ Migration başarıyla tamamlandı!")
            return True
            
    except Exception as e:
        print(f"❌ Migration hatası: {e}")
        print(f"   Detay: {str(e)}")
        return False

def verify_setup():
    """Kurulumu doğrula"""
    
    print()
    print("🔍 Kurulum doğrulanıyor...")
    
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            
            # Beklenen tablolar (models.py'daki __tablename__ ile eşleşmeli)
            expected_tables = [
                'oteller',
                'kullanicilar',
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
                'qr_kod_okutma_loglari'
            ]
            
            existing_tables = inspector.get_table_names()
            missing_tables = [t for t in expected_tables if t not in existing_tables]
            
            if missing_tables:
                print(f"⚠️  Eksik tablolar: {', '.join(missing_tables)}")
                return False
            else:
                print("✅ Tüm tablolar başarıyla oluşturuldu!")
                return True
                
    except Exception as e:
        print(f"❌ Doğrulama hatası: {e}")
        return False

def main():
    """Ana fonksiyon"""
    
    print()
    
    # 1. Veritabanını oluştur
    if not create_database():
        print()
        print("❌ Veritabanı oluşturulamadı. Kurulum iptal edildi.")
        return False
    
    # 2. Tabloları oluştur
    if not create_tables():
        print()
        print("❌ Tablolar oluşturulamadı. Kurulum iptal edildi.")
        return False
    
    # 3. Migration çalıştır (eksik kolonları ekle)
    if not run_migrations():
        print()
        print("⚠️  Migration tamamlanamadı ancak devam ediliyor...")
    
    # 4. Kurulumu doğrula
    if not verify_setup():
        print()
        print("⚠️  Kurulum tamamlandı ancak bazı tablolar eksik olabilir.")
        return False
    
    # Başarılı
    print()
    print("=" * 60)
    print("🎉 KURULUM BAŞARIYLA TAMAMLANDI!")
    print("=" * 60)
    print()
    print("📝 Sonraki Adımlar:")
    print("   1. Uygulamayı başlatın: python app.py")
    print("   2. Tarayıcıda açın: http://localhost:5014")
    print("   3. İlk kurulum sayfasından sistem yöneticisi oluşturun")
    print()
    print("🚀 İyi çalışmalar!")
    print()
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

