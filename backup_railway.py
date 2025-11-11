#!/usr/bin/env python3
"""
Railway Database Backup - SQL Format
Root dizine kaydeder
"""

import subprocess
import os
from datetime import datetime

print("=" * 60)
print("🗄️  RAILWAY DATABASE BACKUP")
print("=" * 60)

# Railway Database URL
DATABASE_URL = "postgresql://postgres:kJQQiRoGKGgWRPWGsRrSdKRoMogEVAGy@postgres.railway.internal:5432/railway"

# Backup dosya adı
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"railway_backup_{timestamp}.sql"

print(f"\n📦 Backup alınıyor...")
print(f"📁 Dosya: {backup_file}")
print()

try:
    # pg_dump komutu
    with open(backup_file, 'w') as f:
        result = subprocess.run(
            ['pg_dump', DATABASE_URL],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True
        )
    
    if result.returncode == 0:
        # Dosya boyutu
        size = os.path.getsize(backup_file)
        size_mb = size / (1024 * 1024)
        
        print("✅ Backup başarılı!")
        print(f"📊 Boyut: {size_mb:.2f} MB ({size:,} bytes)")
        print(f"📁 Konum: {os.path.abspath(backup_file)}")
        print()
        print("=" * 60)
        print("📥 Sonraki Adım:")
        print("   1. Bu dosyayı local'e indir")
        print("   2. Coolify'a yükle ve restore et")
        print("=" * 60)
        print()
        
        # İlk 10 satırı göster
        print("📋 Backup içeriği (ilk 10 satır):")
        print("-" * 60)
        with open(backup_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                print(line.rstrip())
        print("-" * 60)
        
    else:
        print(f"❌ Backup başarısız!")
        print(f"Hata: {result.stderr}")
        
except FileNotFoundError:
    print("❌ pg_dump bulunamadı!")
    print("PostgreSQL client tools yüklü değil.")
    print()
    print("Alternatif: Python ile backup al")
    print("python backup_railway_python.py")
    
except Exception as e:
    print(f"❌ Hata: {e}")
