#!/usr/bin/env python3
"""
Coolify - Sadece Superadmin Oluştur
"""

import os

# Coolify PostgreSQL URL
DATABASE_URL = 'postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip'
os.environ['DATABASE_URL'] = DATABASE_URL

from app import app, db
from models import Kullanici
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_superadmin():
    """Superadmin oluştur"""
    try:
        print("=" * 60)
        print("SUPERADMIN OLUŞTURMA")
        print("=" * 60)
        
        with app.app_context():
            # Superadmin var mı kontrol et
            existing = Kullanici.query.filter_by(kullanici_adi='Mradmin').first()
            
            if existing:
                print("\nℹ️  Superadmin zaten mevcut")
                print(f"   Kullanıcı: {existing.kullanici_adi}")
                print(f"   Ad: {existing.ad} {existing.soyad}")
                print(f"   Rol: {existing.rol}")
                
                cevap = input("\nŞifreyi 'Mr12141618.' olarak sıfırla? (E/H): ")
                if cevap.upper() == 'E':
                    existing.sifre = generate_password_hash('Mr12141618.')
                    db.session.commit()
                    print("✅ Şifre sıfırlandı!")
                return True
            
            # Yeni superadmin oluştur
            print("\n👤 Yeni superadmin oluşturuluyor...")
            superadmin = Kullanici(
                kullanici_adi='Mradmin',
                sifre=generate_password_hash('Mr12141618.'),
                ad='Meril',
                soyad='Royal',
                rol='sistem_yoneticisi',
                aktif=True,
                olusturma_tarihi=datetime.utcnow()
            )
            
            db.session.add(superadmin)
            db.session.commit()
            
            print("✅ Superadmin oluşturuldu!")
            print("\n" + "=" * 60)
            print("GİRİŞ BİLGİLERİ")
            print("=" * 60)
            print("\n🌐 URL: http://h8k8wo040wc48gc4k8skwokw.185.9.38.66.sslip.io")
            print("\n📝 Kullanıcı: Mradmin")
            print("📝 Şifre: Mr12141618.")
            print()
            
            return True
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    create_superadmin()
