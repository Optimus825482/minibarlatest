#!/usr/bin/env python3
"""
Admin Kullanıcı Adını Güncelle
Meril Royal → Yiğit Avcı
"""

import os

# Coolify PostgreSQL URL
DATABASE_URL = 'postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip'
os.environ['DATABASE_URL'] = DATABASE_URL

from app import app, db
from models import Kullanici

print("=" * 60)
print("👤 ADMIN KULLANICI ADI GÜNCELLEME")
print("=" * 60)

try:
    with app.app_context():
        # Mradmin kullanıcısını bul
        admin = Kullanici.query.filter_by(kullanici_adi='Mradmin').first()
        
        if not admin:
            print("\n❌ Mradmin kullanıcısı bulunamadı!")
            print("Mevcut kullanıcılar:")
            users = Kullanici.query.all()
            for user in users:
                print(f"   - {user.kullanici_adi}: {user.ad} {user.soyad}")
            exit(1)
        
        print(f"\n📋 Mevcut Bilgiler:")
        print(f"   Kullanıcı Adı: {admin.kullanici_adi}")
        print(f"   Ad: {admin.ad}")
        print(f"   Soyad: {admin.soyad}")
        print(f"   Rol: {admin.rol}")
        
        # Güncelle
        print(f"\n🔄 Güncelleniyor...")
        admin.ad = 'Yiğit'
        admin.soyad = 'Avcı'
        
        db.session.commit()
        
        print(f"\n✅ Başarıyla güncellendi!")
        print(f"\n📋 Yeni Bilgiler:")
        print(f"   Kullanıcı Adı: {admin.kullanici_adi}")
        print(f"   Ad: {admin.ad}")
        print(f"   Soyad: {admin.soyad}")
        print(f"   Rol: {admin.rol}")
        
        print("\n" + "=" * 60)
        print("🎉 İşlem Tamamlandı!")
        print("=" * 60)
        print("\n📝 Giriş Bilgileri:")
        print("   Kullanıcı: Mradmin")
        print("   Şifre: Mr12141618.")
        print("   Ad Soyad: Yiğit Avcı")
        print()
        
except Exception as e:
    print(f"\n❌ Hata: {e}")
    import traceback
    traceback.print_exc()
