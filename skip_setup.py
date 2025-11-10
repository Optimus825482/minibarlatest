#!/usr/bin/env python3
"""
Setup'ı Atla - Sistem Ayarlarını Oluştur
"""

import os

# Coolify PostgreSQL URL
DATABASE_URL = 'postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip'
os.environ['DATABASE_URL'] = DATABASE_URL

from app import app, db
from models import SistemAyar
from datetime import datetime

def skip_setup():
    """Setup'ı tamamlandı olarak işaretle"""
    try:
        print("=" * 60)
        print("SETUP ATLAMA")
        print("=" * 60)
        
        with app.app_context():
            # Setup tamamlandı ayarını kontrol et
            setup_ayar = SistemAyar.query.filter_by(anahtar='setup_tamamlandi').first()
            
            if setup_ayar:
                print("\n✅ Setup zaten tamamlanmış")
                print(f"   Değer: {setup_ayar.deger}")
                return True
            
            # Setup tamamlandı ayarını oluştur
            print("\n📝 Setup tamamlandı olarak işaretleniyor...")
            
            setup_ayar = SistemAyar(
                anahtar='setup_tamamlandi',
                deger='1',
                aciklama='Sistem kurulumu tamamlandı'
            )
            
            db.session.add(setup_ayar)
            db.session.commit()
            
            print("✅ Setup başarıyla atlandı!")
            print("\n" + "=" * 60)
            print("BİLGİ")
            print("=" * 60)
            print("\n🌐 Artık login sayfasına yönlendirileceksiniz")
            print("📝 Otel bilgilerini admin panelden girebilirsiniz")
            print()
            
            return True
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    skip_setup()
