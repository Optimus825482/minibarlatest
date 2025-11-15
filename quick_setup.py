#!/usr/bin/env python3
"""
⚡ HIZLI KURULUM - Tek Komutla Sistem Hazır!
============================================
Sıfırdan veritabanı + ilk admin oluşturur.

Kullanım:
    python quick_setup.py
"""

import os
import sys
from datetime import datetime, timezone

def run_init_db():
    """init_db.py'yi çalıştır"""
    print("\n" + "=" * 60)
    print("📊 ADIM 1: VERİTABANI VE TABLOLAR OLUŞTURULUYOR")
    print("=" * 60)
    
    try:
        # init_db modülünü import et ve çalıştır
        import init_db
        
        success = init_db.main()
        
        if not success:
            print("\n❌ Veritabanı kurulumu başarısız!")
            return False
        
        print("\n✅ Veritabanı kurulumu tamamlandı!")
        return True
        
    except Exception as e:
        print(f"\n❌ Veritabanı kurulum hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_default_admin():
    """Varsayılan admin oluştur"""
    print("\n" + "=" * 60)
    print("👤 ADIM 2: VARSAYILAN ADMİN OLUŞTURULUYOR")
    print("=" * 60)
    
    try:
        from app import app, db
        from models import Kullanici, Otel
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Admin var mı kontrol et
            existing = Kullanici.query.filter_by(rol='sistem_yoneticisi').first()
            
            if existing:
                print(f"\nℹ️  Admin zaten mevcut: {existing.kullanici_adi}")
                return True
            
            # Varsayılan admin bilgileri
            admin_data = {
                'kullanici_adi': 'admin',
                'sifre': 'admin123',
                'ad': 'Sistem',
                'soyad': 'Yöneticisi',
                'email': 'admin@minibar.com',
                'telefon': None
            }
            
            print("\n📝 Varsayılan Admin Bilgileri:")
            print(f"   Kullanıcı Adı: {admin_data['kullanici_adi']}")
            print(f"   Şifre: {admin_data['sifre']}")
            print(f"   Ad Soyad: {admin_data['ad']} {admin_data['soyad']}")
            
            # Admin oluştur
            admin = Kullanici(
                kullanici_adi=admin_data['kullanici_adi'],
                sifre_hash=generate_password_hash(admin_data['sifre']),
                ad=admin_data['ad'],
                soyad=admin_data['soyad'],
                email=admin_data['email'],
                telefon=admin_data['telefon'],
                rol='sistem_yoneticisi',
                aktif=True,
                olusturma_tarihi=datetime.now(timezone.utc)
            )
            
            db.session.add(admin)
            
            # Varsayılan otel oluştur
            existing_hotel = Otel.query.first()
            if not existing_hotel:
                print("\n🏨 Varsayılan otel oluşturuluyor...")
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
            
            print("\n✅ Varsayılan admin oluşturuldu!")
            return admin_data
            
    except Exception as e:
        print(f"\n❌ Admin oluşturma hatası: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_sample_data():
    """Örnek veri oluştur (opsiyonel)"""
    print("\n" + "=" * 60)
    print("📦 ADIM 3: ÖRNEK VERİLER (Opsiyonel)")
    print("=" * 60)
    
    cevap = input("\nÖrnek veriler oluşturulsun mu? (E/H): ")
    
    if cevap.upper() != 'E':
        print("⏭️  Örnek veri oluşturma atlandı")
        return True
    
    try:
        from app import app, db
        from models import UrunGrup, Urun, Otel, Kat, Oda, OdaTipi
        
        with app.app_context():
            print("\n⏳ Örnek veriler oluşturuluyor...")
            
            # Ürün grupları
            gruplar = [
                {'grup_adi': 'İçecekler', 'aciklama': 'Soğuk ve sıcak içecekler'},
                {'grup_adi': 'Atıştırmalıklar', 'aciklama': 'Çerezler ve atıştırmalıklar'},
                {'grup_adi': 'Alkollü İçecekler', 'aciklama': 'Alkollü içecekler'}
            ]
            
            created_groups = []
            for grup_data in gruplar:
                existing = UrunGrup.query.filter_by(grup_adi=grup_data['grup_adi']).first()
                if not existing:
                    grup = UrunGrup(**grup_data, aktif=True, olusturma_tarihi=datetime.now(timezone.utc))
                    db.session.add(grup)
                    created_groups.append(grup)
            
            db.session.flush()
            
            # Ürünler
            if created_groups:
                urunler = [
                    {'grup_id': created_groups[0].id, 'urun_adi': 'Su (500ml)', 'birim': 'Adet', 'kritik_stok_seviyesi': 50},
                    {'grup_id': created_groups[0].id, 'urun_adi': 'Kola (330ml)', 'birim': 'Adet', 'kritik_stok_seviyesi': 30},
                    {'grup_id': created_groups[0].id, 'urun_adi': 'Meyve Suyu (200ml)', 'birim': 'Adet', 'kritik_stok_seviyesi': 20},
                    {'grup_id': created_groups[1].id, 'urun_adi': 'Çikolata', 'birim': 'Adet', 'kritik_stok_seviyesi': 20},
                    {'grup_id': created_groups[1].id, 'urun_adi': 'Cips', 'birim': 'Adet', 'kritik_stok_seviyesi': 15},
                ]
                
                for urun_data in urunler:
                    urun = Urun(**urun_data, aktif=True, olusturma_tarihi=datetime.now(timezone.utc))
                    db.session.add(urun)
            
            # Kat ve odalar
            otel = Otel.query.first()
            if otel:
                # 1. Kat
                kat1 = Kat(
                    otel_id=otel.id,
                    kat_adi='1. Kat',
                    kat_no=1,
                    aktif=True,
                    olusturma_tarihi=datetime.now(timezone.utc)
                )
                db.session.add(kat1)
                db.session.flush()
                
                # Örnek odalar
                # Önce Standard oda tipini al veya oluştur
                standard_oda_tipi = OdaTipi.query.filter_by(ad='STANDARD').first()
                if not standard_oda_tipi:
                    standard_oda_tipi = OdaTipi(
                        ad='STANDARD',
                        dolap_sayisi=1,
                        setup='STANDARD',
                        aktif=True
                    )
                    db.session.add(standard_oda_tipi)
                    db.session.flush()
                
                for oda_no in range(101, 106):
                    oda = Oda(
                        kat_id=kat1.id,
                        oda_no=str(oda_no),
                        oda_tipi_id=standard_oda_tipi.id,
                        kapasite=2,
                        aktif=True,
                        olusturma_tarihi=datetime.now(timezone.utc)
                    )
                    db.session.add(oda)
            
            db.session.commit()
            
            print("✅ Örnek veriler oluşturuldu!")
            print("   - 3 Ürün Grubu")
            print("   - 5 Ürün")
            print("   - 1 Kat")
            print("   - 5 Oda")
            
            return True
            
    except Exception as e:
        print(f"⚠️  Örnek veri oluşturma hatası: {e}")
        print("   (Sistem yine de kullanılabilir)")
        return True

def print_final_info(admin_data):
    """Son bilgilendirme"""
    print("\n" + "=" * 60)
    print("🎉 HIZLI KURULUM TAMAMLANDI!")
    print("=" * 60)
    
    if admin_data:
        print("\n📋 GİRİŞ BİLGİLERİ:")
        print(f"   Kullanıcı Adı: {admin_data['kullanici_adi']}")
        print(f"   Şifre: {admin_data['sifre']}")
        print(f"   Rol: Sistem Yöneticisi")
    
    print("\n🌐 UYGULAMA:")
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
    print("   1. Uygulamayı başlatın:")
    print("      python app.py")
    print()
    print("   2. Tarayıcıda açın ve giriş yapın")
    print()
    print("   3. İlk yapılacaklar:")
    print("      - Otel bilgilerini güncelleyin")
    print("      - Şifrenizi değiştirin")
    print("      - Kullanıcıları ekleyin")
    print("      - Ürünleri tanımlayın")
    
    print("\n⚠️  GÜVENLİK UYARISI:")
    print("   Varsayılan şifre kullanılıyor!")
    print("   İlk girişten sonra mutlaka değiştirin!")
    
    print("\n🚀 İyi çalışmalar!")
    print("=" * 60 + "\n")

def main():
    """Ana fonksiyon"""
    print("\n" + "=" * 60)
    print("⚡ OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   HIZLI KURULUM")
    print("=" * 60)
    print("\nBu script şunları yapacak:")
    print("   1. Veritabanı ve tabloları oluştur")
    print("   2. Varsayılan admin oluştur")
    print("   3. Örnek veriler ekle (opsiyonel)")
    print()
    
    cevap = input("Devam edilsin mi? (E/H): ")
    if cevap.upper() != 'E':
        print("\n❌ İşlem iptal edildi")
        return False
    
    # 1. Veritabanı kurulumu
    if not run_init_db():
        return False
    
    # 2. Admin oluştur
    admin_data = create_default_admin()
    if not admin_data:
        return False
    
    # 3. Örnek veriler (opsiyonel)
    create_sample_data()
    
    # 4. Son bilgilendirme
    print_final_info(admin_data)
    
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
