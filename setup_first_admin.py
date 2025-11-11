#!/usr/bin/env python3
"""
🚀 İLK KURULUM - SİSTEM YÖNETİCİSİ OLUŞTURMA
================================================
Sıfırdan yeni veritabanı kurulumu için ilk admin oluşturur.

Özellikler:
- Veritabanı bağlantı kontrolü
- Tablo varlık kontrolü
- Güvenli şifre oluşturma
- Detaylı hata yönetimi
- Kullanıcı dostu arayüz

Kullanım:
    python setup_first_admin.py
"""

import os
import sys
from datetime import datetime, timezone
from getpass import getpass

def check_environment():
    """Ortam değişkenlerini kontrol et"""
    print("🔍 Ortam kontrol ediliyor...")
    
    # Database URL kontrolü
    db_url = os.getenv('DATABASE_URL')
    db_type = os.getenv('DB_TYPE', 'postgresql')
    
    if db_url:
        print(f"✅ DATABASE_URL bulundu")
        print(f"   Tip: {db_type}")
        return True
    
    # PostgreSQL değişkenleri
    pg_host = os.getenv('PGHOST_PRIVATE') or os.getenv('PGHOST')
    pg_user = os.getenv('PGUSER')
    pg_pass = os.getenv('PGPASSWORD')
    pg_db = os.getenv('PGDATABASE')
    
    if pg_host and pg_user and pg_pass and pg_db:
        print(f"✅ PostgreSQL değişkenleri bulundu")
        print(f"   Host: {pg_host}")
        print(f"   Database: {pg_db}")
        return True
    
    # Local .env kontrolü
    if not os.path.exists('.env'):
        print("⚠️  .env dosyası bulunamadı")
        print("   Local kurulum için .env dosyası gerekli")
        return False
    
    print("✅ .env dosyası bulundu")
    return True

def test_database_connection():
    """Veritabanı bağlantısını test et"""
    try:
        print("\n📡 Veritabanı bağlantısı test ediliyor...")
        
        from app import app, db
        
        with app.app_context():
            # Basit bir sorgu ile test et
            db.session.execute(db.text('SELECT 1'))
            print("✅ Veritabanı bağlantısı başarılı")
            return True
            
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        return False

def check_tables():
    """Tabloların varlığını kontrol et"""
    try:
        print("\n📊 Tablolar kontrol ediliyor...")
        
        from app import app, db
        from sqlalchemy import inspect
        
        with app.app_context():
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if not tables:
                print("⚠️  Hiç tablo bulunamadı!")
                print("   Önce 'python init_db.py' çalıştırın")
                return False
            
            # Kritik tabloları kontrol et
            required_tables = ['kullanicilar', 'oteller']
            missing = [t for t in required_tables if t not in tables]
            
            if missing:
                print(f"⚠️  Eksik tablolar: {', '.join(missing)}")
                print("   Önce 'python init_db.py' çalıştırın")
                return False
            
            print(f"✅ {len(tables)} tablo bulundu")
            return True
            
    except Exception as e:
        print(f"❌ Tablo kontrol hatası: {e}")
        return False

def check_existing_admin():
    """Mevcut admin var mı kontrol et"""
    try:
        from app import app, db
        from models import Kullanici
        
        with app.app_context():
            admin_count = Kullanici.query.filter_by(rol='sistem_yoneticisi').count()
            
            if admin_count > 0:
                print(f"\n⚠️  Sistemde zaten {admin_count} sistem yöneticisi var!")
                
                admins = Kullanici.query.filter_by(rol='sistem_yoneticisi').all()
                print("\nMevcut Sistem Yöneticileri:")
                for admin in admins:
                    print(f"   - {admin.kullanici_adi} ({admin.ad} {admin.soyad})")
                
                return True
            
            return False
            
    except Exception as e:
        print(f"❌ Admin kontrol hatası: {e}")
        return False

def get_user_input():
    """Kullanıcıdan bilgileri al"""
    print("\n" + "=" * 60)
    print("👤 YENİ SİSTEM YÖNETİCİSİ BİLGİLERİ")
    print("=" * 60)
    
    # Kullanıcı adı
    while True:
        kullanici_adi = input("\n📝 Kullanıcı Adı (min 3 karakter): ").strip()
        if len(kullanici_adi) >= 3:
            break
        print("❌ Kullanıcı adı en az 3 karakter olmalı!")
    
    # Ad
    while True:
        ad = input("📝 Ad: ").strip()
        if ad:
            break
        print("❌ Ad boş olamaz!")
    
    # Soyad
    while True:
        soyad = input("📝 Soyad: ").strip()
        if soyad:
            break
        print("❌ Soyad boş olamaz!")
    
    # Email (opsiyonel)
    email = input("📧 Email (opsiyonel): ").strip() or None
    
    # Telefon (opsiyonel)
    telefon = input("📞 Telefon (opsiyonel): ").strip() or None
    
    # Şifre
    while True:
        sifre = getpass("🔒 Şifre (min 6 karakter): ")
        if len(sifre) >= 6:
            sifre_tekrar = getpass("🔒 Şifre Tekrar: ")
            if sifre == sifre_tekrar:
                break
            print("❌ Şifreler eşleşmiyor!")
        else:
            print("❌ Şifre en az 6 karakter olmalı!")
    
    return {
        'kullanici_adi': kullanici_adi,
        'ad': ad,
        'soyad': soyad,
        'email': email,
        'telefon': telefon,
        'sifre': sifre
    }

def create_admin(user_data):
    """Sistem yöneticisi oluştur"""
    try:
        print("\n⏳ Sistem yöneticisi oluşturuluyor...")
        
        from app import app, db
        from models import Kullanici
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Kullanıcı adı kontrolü
            existing = Kullanici.query.filter_by(
                kullanici_adi=user_data['kullanici_adi']
            ).first()
            
            if existing:
                print(f"❌ '{user_data['kullanici_adi']}' kullanıcı adı zaten kullanılıyor!")
                return False
            
            # Yeni admin oluştur
            admin = Kullanici(
                kullanici_adi=user_data['kullanici_adi'],
                sifre_hash=generate_password_hash(user_data['sifre']),
                ad=user_data['ad'],
                soyad=user_data['soyad'],
                email=user_data['email'],
                telefon=user_data['telefon'],
                rol='sistem_yoneticisi',
                aktif=True,
                olusturma_tarihi=datetime.now(timezone.utc)
            )
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Sistem yöneticisi başarıyla oluşturuldu!")
            return True
            
    except Exception as e:
        print(f"❌ Oluşturma hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_default_hotel():
    """Varsayılan otel oluştur"""
    try:
        print("\n🏨 Varsayılan otel oluşturuluyor...")
        
        from app import app, db
        from models import Otel
        
        with app.app_context():
            # Otel var mı kontrol et
            existing = Otel.query.first()
            if existing:
                print(f"ℹ️  Otel zaten mevcut: {existing.ad}")
                return True
            
            # Varsayılan otel oluştur
            otel = Otel(
                ad='Varsayılan Otel',
                adres='',
                telefon='',
                email='',
                aktif=True,
                olusturma_tarihi=datetime.now(timezone.utc)
            )
            
            db.session.add(otel)
            db.session.commit()
            
            print("✅ Varsayılan otel oluşturuldu")
            return True
            
    except Exception as e:
        print(f"⚠️  Otel oluşturma hatası: {e}")
        return False

def print_success_info(user_data):
    """Başarı mesajı ve giriş bilgileri"""
    print("\n" + "=" * 60)
    print("🎉 KURULUM BAŞARIYLA TAMAMLANDI!")
    print("=" * 60)
    
    print("\n📋 GİRİŞ BİLGİLERİ:")
    print(f"   Kullanıcı Adı: {user_data['kullanici_adi']}")
    print(f"   Şifre: {user_data['sifre']}")
    print(f"   Rol: Sistem Yöneticisi")
    
    print("\n🌐 UYGULAMA:")
    
    # URL'i tespit et
    port = os.getenv('PORT', '5014')
    
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("   Railway deployment tespit edildi")
        print("   URL'yi Railway dashboard'dan kontrol edin")
    elif os.getenv('COOLIFY_URL'):
        coolify_url = os.getenv('COOLIFY_URL')
        print(f"   URL: {coolify_url}")
    else:
        print(f"   URL: http://localhost:{port}")
    
    print("\n📝 SONRAKİ ADIMLAR:")
    print("   1. Uygulamayı başlatın (python app.py)")
    print("   2. Tarayıcıda açın")
    print("   3. Yukarıdaki bilgilerle giriş yapın")
    print("   4. Otel bilgilerini güncelleyin")
    print("   5. Kullanıcıları ve ürünleri ekleyin")
    
    print("\n🔒 GÜVENLİK:")
    print("   ⚠️  Bu bilgileri güvenli bir yerde saklayın!")
    print("   ⚠️  İlk girişten sonra şifrenizi değiştirin!")
    
    print("\n🚀 İyi çalışmalar!")
    print("=" * 60 + "\n")

def main():
    """Ana fonksiyon"""
    print("\n" + "=" * 60)
    print("🚀 OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   İLK KURULUM - SİSTEM YÖNETİCİSİ OLUŞTURMA")
    print("=" * 60)
    
    # 1. Ortam kontrolü
    if not check_environment():
        print("\n❌ Ortam kontrolü başarısız!")
        print("   .env dosyasını kontrol edin")
        return False
    
    # 2. Veritabanı bağlantısı
    if not test_database_connection():
        print("\n❌ Veritabanı bağlantısı kurulamadı!")
        print("   Veritabanı ayarlarını kontrol edin")
        return False
    
    # 3. Tablo kontrolü
    if not check_tables():
        print("\n❌ Tablolar bulunamadı!")
        print("   Önce 'python init_db.py' çalıştırın")
        return False
    
    # 4. Mevcut admin kontrolü
    if check_existing_admin():
        cevap = input("\nYine de yeni admin oluşturmak istiyor musunuz? (E/H): ")
        if cevap.upper() != 'E':
            print("\n❌ İşlem iptal edildi")
            return False
    
    # 5. Kullanıcı bilgilerini al
    try:
        user_data = get_user_input()
    except KeyboardInterrupt:
        print("\n\n❌ İşlem kullanıcı tarafından iptal edildi")
        return False
    
    # 6. Onay al
    print("\n" + "=" * 60)
    print("📋 ÖZET:")
    print(f"   Kullanıcı Adı: {user_data['kullanici_adi']}")
    print(f"   Ad Soyad: {user_data['ad']} {user_data['soyad']}")
    if user_data['email']:
        print(f"   Email: {user_data['email']}")
    if user_data['telefon']:
        print(f"   Telefon: {user_data['telefon']}")
    print(f"   Rol: Sistem Yöneticisi")
    print("=" * 60)
    
    cevap = input("\nBu bilgilerle devam edilsin mi? (E/H): ")
    if cevap.upper() != 'E':
        print("\n❌ İşlem iptal edildi")
        return False
    
    # 7. Admin oluştur
    if not create_admin(user_data):
        print("\n❌ Sistem yöneticisi oluşturulamadı!")
        return False
    
    # 8. Varsayılan otel oluştur
    create_default_hotel()
    
    # 9. Başarı mesajı
    print_success_info(user_data)
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ İşlem kullanıcı tarafından iptal edildi")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
