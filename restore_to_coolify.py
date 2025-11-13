#!/usr/bin/env python3
"""
Coolify Database Restore Script
Backup'ı Coolify'a yükler
"""

import os
import sys
import subprocess

print("=" * 60)
print("📥 COOLIFY DATABASE RESTORE")
print("=" * 60)

# Backup dosyası
BACKUP_FILE = "railway_backup.sql"

# Coolify Database URL
DATABASE_URL = "postgresql://postgres:518518Erkan@b4oo4wg8kwgw4c8kc4k444c8:5432/minibar_takip"

# Dosya kontrolü
if not os.path.exists(BACKUP_FILE):
    print(f"\n❌ Hata: {BACKUP_FILE} bulunamadı!")
    print("\nÖnce Railway'den backup alın:")
    print("  python backup_railway_python.py")
    sys.exit(1)

# Dosya boyutu
size = os.path.getsize(BACKUP_FILE)
size_mb = size / (1024 * 1024)

print(f"\n📁 Backup dosyası: {BACKUP_FILE}")
print(f"📊 Boyut: {size_mb:.2f} MB ({size:,} bytes)")
print()
print("⚠️  UYARI: Mevcut veriler silinecek!")

confirm = input("Devam etmek istiyor musunuz? (E/H): ")

if confirm.upper() != 'E':
    print("❌ İşlem iptal edildi")
    sys.exit(0)

print("\n🔄 Restore başlıyor...")
print()

try:
    # psql ile restore
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        result = subprocess.run(
            ['psql', DATABASE_URL],
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✅ RESTORE BAŞARILI!")
        print("=" * 60)
        print()
        print("🎉 Coolify database'i backup verileriyle dolu!")
        print()
        print("📝 Sonraki adım:")
        print("   http://h8k8wo040wc48gc4k8skwokw.185.9.38.66.sslip.io/login")
        print("   Kullanıcı: Mradmin")
        print("   Şifre: Mr12141618.")
        print()
    else:
        print()
        print("❌ Restore başarısız!")
        print(f"Hata: {result.stderr}")
        sys.exit(1)
        
except FileNotFoundError:
    print("❌ psql bulunamadı!")
    print("PostgreSQL client tools yüklü değil.")
    print()
    print("Alternatif: Python ile restore")
    print("python restore_to_coolify_python.py")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Hata: {e}")
    sys.exit(1)
